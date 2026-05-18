import asyncio
import time
from typing import Any, Optional

import pytest

from mojentic.llm.tools.llm_tool import LLMTool
from mojentic.llm.tools.runner import (
    AsyncParallelToolRunner,
    SerialToolRunner,
    ToolCallExecution,
    ToolRunContext,
)


class _EchoTool(LLMTool):
    def run(self, value: str) -> dict:
        return {"echo": value}

    @property
    def descriptor(self):
        return {
            "type": "function",
            "function": {
                "name": "echo",
                "description": "Echo input",
                "parameters": {
                    "type": "object",
                    "properties": {"value": {"type": "string"}},
                    "required": ["value"],
                },
            },
        }


class _RaisingTool(LLMTool):
    def run(self, value: str) -> dict:
        raise RuntimeError(f"boom-{value}")

    @property
    def descriptor(self):
        return {
            "type": "function",
            "function": {
                "name": "raises",
                "description": "Always raises",
                "parameters": {
                    "type": "object",
                    "properties": {"value": {"type": "string"}},
                    "required": ["value"],
                },
            },
        }


class _AsyncSlowTool(LLMTool):
    """Async tool that sleeps for ``delay_s`` seconds before returning."""

    async def run(self, value: str, delay_s: float = 0.05, ctx: Optional[ToolRunContext] = None) -> dict:
        try:
            await asyncio.sleep(delay_s)
        except asyncio.CancelledError:
            raise
        if ctx is not None and ctx.cancelled:
            raise asyncio.CancelledError("ctx cancelled")
        return {"value": value, "delay_s": delay_s}

    @property
    def descriptor(self):
        return {
            "type": "function",
            "function": {
                "name": "slow",
                "description": "Sleeps then returns",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "value": {"type": "string"},
                        "delay_s": {"type": "number"},
                    },
                    "required": ["value"],
                },
            },
        }


@pytest.fixture
def echo_tool():
    return _EchoTool()


@pytest.fixture
def raising_tool():
    return _RaisingTool()


@pytest.fixture
def slow_tool():
    return _AsyncSlowTool()


class DescribeSerialToolRunner:
    class DescribeBatchExecution:
        def should_preserve_input_order(self, echo_tool):
            runner = SerialToolRunner()
            calls = [
                ToolCallExecution(id="1", name="echo", args={"value": "a"}),
                ToolCallExecution(id="2", name="echo", args={"value": "b"}),
                ToolCallExecution(id="3", name="echo", args={"value": "c"}),
            ]

            outcomes = runner.run_batch(calls, [echo_tool])

            assert [o.id for o in outcomes] == ["1", "2", "3"]
            assert [o.result["echo"] for o in outcomes] == ["a", "b", "c"]
            assert all(o.ok for o in outcomes)

        def should_return_empty_for_no_calls(self, echo_tool):
            runner = SerialToolRunner()

            outcomes = runner.run_batch([], [echo_tool])

            assert outcomes == []

        def should_mark_outcome_as_failed_when_tool_raises(self, raising_tool):
            runner = SerialToolRunner()
            calls = [ToolCallExecution(id="1", name="raises", args={"value": "x"})]

            outcomes = runner.run_batch(calls, [raising_tool])

            assert outcomes[0].ok is False
            assert isinstance(outcomes[0].error, RuntimeError)
            assert "boom-x" in str(outcomes[0].error)

        def should_mark_outcome_as_failed_when_tool_not_found(self):
            runner = SerialToolRunner()
            calls = [ToolCallExecution(id="1", name="missing", args={})]

            outcomes = runner.run_batch(calls, [])

            assert outcomes[0].ok is False
            assert isinstance(outcomes[0].error, LookupError)

    class DescribeHooks:
        def should_invoke_start_and_complete_hooks_in_order(self, echo_tool):
            runner = SerialToolRunner()
            events = []
            ctx = ToolRunContext(
                on_call_start=lambda c: events.append(("start", c.id)),
                on_call_complete=lambda o: events.append(("complete", o.id)),
            )
            calls = [ToolCallExecution(id="1", name="echo", args={"value": "x"})]

            runner.run_batch(calls, [echo_tool], ctx)

            assert events == [("start", "1"), ("complete", "1")]


class DescribeAsyncParallelToolRunner:
    class DescribeConcurrency:
        def should_dispatch_calls_in_parallel(self, slow_tool):
            runner = AsyncParallelToolRunner(max_concurrency=4)
            delay = 0.1
            calls = [
                ToolCallExecution(id=str(i), name="slow", args={"value": str(i), "delay_s": delay})
                for i in range(4)
            ]

            start = time.time()
            outcomes = asyncio.run(runner.run_batch(calls, [slow_tool]))
            elapsed = time.time() - start

            assert len(outcomes) == 4
            assert all(o.ok for o in outcomes)
            assert elapsed < delay * 3, f"expected parallel dispatch, took {elapsed:.3f}s"

        def should_respect_max_concurrency(self, slow_tool):
            runner = AsyncParallelToolRunner(max_concurrency=2)
            delay = 0.1
            calls = [
                ToolCallExecution(id=str(i), name="slow", args={"value": str(i), "delay_s": delay})
                for i in range(4)
            ]

            start = time.time()
            asyncio.run(runner.run_batch(calls, [slow_tool]))
            elapsed = time.time() - start

            assert elapsed >= delay * 1.5, "expected at least two waves at concurrency=2"

        def should_preserve_input_order_in_outcomes(self, slow_tool):
            runner = AsyncParallelToolRunner(max_concurrency=4)
            calls = [
                ToolCallExecution(id="a", name="slow", args={"value": "a", "delay_s": 0.05}),
                ToolCallExecution(id="b", name="slow", args={"value": "b", "delay_s": 0.01}),
                ToolCallExecution(id="c", name="slow", args={"value": "c", "delay_s": 0.03}),
            ]

            outcomes = asyncio.run(runner.run_batch(calls, [slow_tool]))

            assert [o.id for o in outcomes] == ["a", "b", "c"]
            assert [o.result["value"] for o in outcomes] == ["a", "b", "c"]

    class DescribeCancellation:
        def should_skip_pending_calls_when_context_cancelled_before_start(self, slow_tool):
            runner = AsyncParallelToolRunner(max_concurrency=2)

            async def run() -> Any:
                ctx = ToolRunContext(cancel_event=asyncio.Event())
                ctx.cancel_event.set()
                calls = [
                    ToolCallExecution(id="1", name="slow", args={"value": "1"}),
                    ToolCallExecution(id="2", name="slow", args={"value": "2"}),
                ]
                return await runner.run_batch(calls, [slow_tool], ctx)

            outcomes = asyncio.run(run())

            assert all(o.ok is False for o in outcomes)
            assert all(isinstance(o.error, asyncio.CancelledError) for o in outcomes)

    class DescribeValidation:
        def should_reject_non_positive_concurrency(self):
            with pytest.raises(ValueError):
                AsyncParallelToolRunner(max_concurrency=0)
