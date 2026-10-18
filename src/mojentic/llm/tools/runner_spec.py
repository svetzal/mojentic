import asyncio
from typing import Any

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
    """Async tool that yields while tracking concurrent public tool execution."""

    def __init__(self):
        self.active = 0
        self.peak = 0
        self.started = []

    async def run(
        self, value: str, delay_s: float = 0.05, ctx: ToolRunContext | None = None
    ) -> dict:
        self.active += 1
        self.peak = max(self.peak, self.active)
        self.started.append(value)
        await asyncio.sleep(0)
        self.active -= 1
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
                ToolCallExecution(
                    id=str(i), name="slow", args={"value": str(i), "delay_s": delay}
                )
                for i in range(4)
            ]

            outcomes = asyncio.run(runner.run_batch(calls, [slow_tool]))

            assert len(outcomes) == 4
            assert all(o.ok for o in outcomes)
            assert slow_tool.peak == 4
            assert slow_tool.active == 0
            assert slow_tool.started == ["0", "1", "2", "3"]

        def should_respect_max_concurrency(self, slow_tool):
            runner = AsyncParallelToolRunner(max_concurrency=2)
            delay = 0.1
            calls = [
                ToolCallExecution(
                    id=str(i), name="slow", args={"value": str(i), "delay_s": delay}
                )
                for i in range(4)
            ]

            outcomes = asyncio.run(runner.run_batch(calls, [slow_tool]))

            assert slow_tool.peak == 2
            assert slow_tool.active == 0
            assert [outcome.result["value"] for outcome in outcomes] == [
                "0",
                "1",
                "2",
                "3",
            ]

        def should_preserve_input_order_in_outcomes(self):
            async def run():
                gates = {value: asyncio.Event() for value in "abc"}
                finished = {value: asyncio.Event() for value in "abc"}
                all_started = asyncio.Event()
                started, completed = [], []

                class ControlledTool(_AsyncSlowTool):
                    async def run(self, value: str, **kwargs) -> dict:
                        started.append(value)
                        if len(started) == 3:
                            all_started.set()
                        await gates[value].wait()
                        completed.append(value)
                        finished[value].set()
                        return {"value": value}

                runner = AsyncParallelToolRunner(max_concurrency=3)
                calls = [
                    ToolCallExecution(id=value, name="slow", args={"value": value})
                    for value in "abc"
                ]
                pending = asyncio.create_task(
                    runner.run_batch(calls, [ControlledTool()])
                )
                await all_started.wait()
                for value in "cba":
                    gates[value].set()
                    await finished[value].wait()
                return await pending, completed

            outcomes, completed = asyncio.run(run())

            assert completed == ["c", "b", "a"]
            assert [outcome.id for outcome in outcomes] == ["a", "b", "c"]
            assert [outcome.result["value"] for outcome in outcomes] == ["a", "b", "c"]

    class DescribeCancellation:
        def should_skip_pending_calls_when_context_cancelled_before_start(
            self, slow_tool
        ):
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
