"""
Tool runner abstraction for executing batches of tool calls.

Provides pluggable execution strategies (serial sync, async parallel) so
brokers can stay independent of concurrency policy. Mirrors the TypeScript
``ToolRunner`` design from ``mojentic-ts``.
"""
from __future__ import annotations

import asyncio
import inspect
import time
from abc import ABC, abstractmethod
from typing import Any, Awaitable, Callable, Dict, List, Optional, Sequence, Union

from pydantic import BaseModel, ConfigDict, Field

from mojentic.llm.tools.llm_tool import LLMTool


class ToolRunContext(BaseModel):
    """
    Context passed to a tool runner (and, optionally, to the tools it runs)
    for a single batch.

    Tools may accept a ``ctx`` keyword argument to observe cancellation;
    tools that ignore it continue to work unchanged.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    cancel_event: Optional[asyncio.Event] = None
    """Async event that fires when the runner aborts the batch."""

    correlation_id: Optional[str] = None
    """Correlation id propagated to per-tool tracing."""

    source: Optional[str] = None
    """Source identifier propagated to per-tool tracing."""

    on_call_start: Optional[Callable[["ToolCallExecution"], None]] = None
    """Hook fired when a tool starts running."""

    on_call_complete: Optional[Callable[["ToolCallOutcome"], None]] = None
    """Hook fired when a tool produces an outcome."""

    @property
    def cancelled(self) -> bool:
        return self.cancel_event is not None and self.cancel_event.is_set()


class ToolCallExecution(BaseModel):
    """A single tool call to execute, identified by an opaque id."""

    id: str
    name: str
    args: Dict[str, Any] = Field(default_factory=dict)


class ToolCallOutcome(BaseModel):
    """
    Outcome of executing a single tool call.

    Discriminated by the ``ok`` flag — ``True`` means the tool returned a
    result, ``False`` means the tool returned an error or raised.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    id: str
    name: str
    ok: bool
    result: Optional[Any] = None
    error: Optional[BaseException] = None
    duration_ms: float = 0.0


class ToolRunner(ABC):
    """
    Strategy for executing a batch of tool calls.

    Implementations decide concurrency, ordering, and cancellation
    semantics. Output order must match input order regardless of execution
    order.
    """

    @abstractmethod
    def run_batch(
        self,
        calls: Sequence[ToolCallExecution],
        tools: Sequence[LLMTool],
        context: Optional[ToolRunContext] = None,
    ) -> Union[List[ToolCallOutcome], Awaitable[List[ToolCallOutcome]]]:
        ...


def _accepts_ctx(tool: LLMTool) -> bool:
    """Return True if the tool's ``run`` method accepts a ``ctx`` keyword."""
    try:
        sig = inspect.signature(tool.run)
    except (TypeError, ValueError):
        return False
    params = sig.parameters
    if "ctx" in params:
        return True
    return any(
        p.kind is inspect.Parameter.VAR_KEYWORD for p in params.values()
    )


def _not_found(name: str) -> Exception:
    return LookupError(f"Tool {name!r} not found")


def _build_aborted_outcome(call: ToolCallExecution) -> ToolCallOutcome:
    return ToolCallOutcome(
        id=call.id,
        name=call.name,
        ok=False,
        error=asyncio.CancelledError("Tool batch aborted"),
        duration_ms=0.0,
    )


def _make_not_found_outcome(call: ToolCallExecution, duration_ms: float) -> ToolCallOutcome:
    return ToolCallOutcome(
        id=call.id,
        name=call.name,
        ok=False,
        error=_not_found(call.name),
        duration_ms=duration_ms,
    )


def _resolve_tool(tools: Sequence[LLMTool], name: str) -> Optional[LLMTool]:
    for tool in tools:
        if tool.matches(name):
            return tool
    return None


def _invoke_sync(tool: LLMTool, args: Dict[str, Any], ctx: Optional[ToolRunContext]) -> Any:
    if ctx is not None and _accepts_ctx(tool):
        return tool.run(**args, ctx=ctx)
    return tool.run(**args)


async def _invoke_async(
    tool: LLMTool, args: Dict[str, Any], ctx: Optional[ToolRunContext]
) -> Any:
    if inspect.iscoroutinefunction(tool.run):
        return await _invoke_sync(tool, args, ctx)
    # Sync tools must not block the loop when run by the async runner —
    # dispatch them to a worker thread so parallel batches actually parallelise.
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, lambda: _invoke_sync(tool, args, ctx))


def _start_hook(ctx: Optional[ToolRunContext], call: ToolCallExecution) -> None:
    if ctx is not None and ctx.on_call_start is not None:
        ctx.on_call_start(call)


def _complete_hook(ctx: Optional[ToolRunContext], outcome: ToolCallOutcome) -> None:
    if ctx is not None and ctx.on_call_complete is not None:
        ctx.on_call_complete(outcome)


class SerialToolRunner(ToolRunner):
    """
    Execute tool calls one at a time in input order, synchronously.

    This is the default for :class:`mojentic.llm.llm_broker.LLMBroker` for
    backward compatibility and predictable, stepwise debugging.
    """

    def run_batch(
        self,
        calls: Sequence[ToolCallExecution],
        tools: Sequence[LLMTool],
        context: Optional[ToolRunContext] = None,
    ) -> List[ToolCallOutcome]:
        outcomes: List[ToolCallOutcome] = []
        for call in calls:
            if context is not None and context.cancelled:
                aborted = _build_aborted_outcome(call)
                outcomes.append(aborted)
                _complete_hook(context, aborted)
                continue
            outcomes.append(self._execute(call, tools, context))
        return outcomes

    @staticmethod
    def _execute(
        call: ToolCallExecution,
        tools: Sequence[LLMTool],
        context: Optional[ToolRunContext],
    ) -> ToolCallOutcome:
        start = time.time()
        _start_hook(context, call)
        tool = _resolve_tool(tools, call.name)
        if tool is None:
            outcome = _make_not_found_outcome(call, (time.time() - start) * 1000.0)
            _complete_hook(context, outcome)
            return outcome
        try:
            result = _invoke_sync(tool, call.args, context)
            outcome = ToolCallOutcome(
                id=call.id,
                name=call.name,
                ok=True,
                result=result,
                duration_ms=(time.time() - start) * 1000.0,
            )
        except Exception as err:  # noqa: BLE001 - capture any tool failure
            outcome = ToolCallOutcome(
                id=call.id,
                name=call.name,
                ok=False,
                error=err,
                duration_ms=(time.time() - start) * 1000.0,
            )
        _complete_hook(context, outcome)
        return outcome


class AsyncParallelToolRunner(ToolRunner):
    """
    Execute tool calls concurrently with a bounded fan-out using asyncio.

    ``max_concurrency`` defaults to 4 — high enough to win on typical
    realtime turns (2–3 concurrent function calls) but low enough that
    unbounded fan-out into rate-limited APIs doesn't punish users.
    """

    def __init__(self, max_concurrency: int = 4):
        if max_concurrency < 1:
            raise ValueError(
                f"max_concurrency must be a positive integer, got {max_concurrency}"
            )
        self.max_concurrency = max_concurrency

    async def run_batch(
        self,
        calls: Sequence[ToolCallExecution],
        tools: Sequence[LLMTool],
        context: Optional[ToolRunContext] = None,
    ) -> List[ToolCallOutcome]:
        if not calls:
            return []

        outcomes: List[Optional[ToolCallOutcome]] = [None] * len(calls)
        semaphore = asyncio.Semaphore(self.max_concurrency)

        async def worker(idx: int, call: ToolCallExecution) -> None:
            if context is not None and context.cancelled:
                aborted = _build_aborted_outcome(call)
                outcomes[idx] = aborted
                _complete_hook(context, aborted)
                return
            async with semaphore:
                if context is not None and context.cancelled:
                    aborted = _build_aborted_outcome(call)
                    outcomes[idx] = aborted
                    _complete_hook(context, aborted)
                    return
                outcomes[idx] = await self._execute(call, tools, context)

        await asyncio.gather(*(worker(i, c) for i, c in enumerate(calls)))
        return [o for o in outcomes if o is not None]

    @staticmethod
    async def _execute(
        call: ToolCallExecution,
        tools: Sequence[LLMTool],
        context: Optional[ToolRunContext],
    ) -> ToolCallOutcome:
        start = time.time()
        _start_hook(context, call)
        tool = _resolve_tool(tools, call.name)
        if tool is None:
            outcome = _make_not_found_outcome(call, (time.time() - start) * 1000.0)
            _complete_hook(context, outcome)
            return outcome
        try:
            result = await _invoke_async(tool, call.args, context)
            outcome = ToolCallOutcome(
                id=call.id,
                name=call.name,
                ok=True,
                result=result,
                duration_ms=(time.time() - start) * 1000.0,
            )
        except asyncio.CancelledError as err:
            outcome = ToolCallOutcome(
                id=call.id,
                name=call.name,
                ok=False,
                error=err,
                duration_ms=(time.time() - start) * 1000.0,
            )
        except Exception as err:  # noqa: BLE001
            outcome = ToolCallOutcome(
                id=call.id,
                name=call.name,
                ok=False,
                error=err,
                duration_ms=(time.time() - start) * 1000.0,
            )
        _complete_hook(context, outcome)
        return outcome
