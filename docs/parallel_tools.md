# Parallel Tool Execution

Mojentic factors tool-batch execution behind a `ToolRunner`
abstraction so brokers don't grow their own concurrency code:

| Runner | Behaviour | Default for |
|---|---|---|
| `SerialToolRunner` | Awaits each call in order, synchronously. | `LLMBroker` (backward-compatible) |
| `AsyncParallelToolRunner` | Concurrent dispatch via `asyncio.gather`, bounded by `max_concurrency` (default 4). Sync tools run in a worker thread so they don't block the event loop. | `RealtimeVoiceBroker` |

## Opt-in for `LLMBroker`

Pass a `tool_runner` to the broker:

```python
from mojentic.llm.llm_broker import LLMBroker
from mojentic.llm.tools.runner import AsyncParallelToolRunner

broker = LLMBroker(
    model="gpt-4o",
    gateway=...,
    tool_runner=AsyncParallelToolRunner(max_concurrency=4),
)
```

When the model returns multiple `tool_calls` in a single assistant
turn, the broker fans them out concurrently. Output order is
preserved so the tool messages submitted back to the model match the
original call order.

## Cancellation

Tools may opt in to cancellation by accepting an optional
`ctx: ToolRunContext` keyword:

```python
from mojentic.llm.tools.llm_tool import LLMTool
from mojentic.llm.tools.runner import ToolRunContext


class _CancellableTool(LLMTool):
    async def run(self, prompt: str, ctx: ToolRunContext = None) -> dict:
        for _ in range(10):
            if ctx is not None and ctx.cancelled:
                raise asyncio.CancelledError("aborted by batch")
            await do_one_chunk()
        return {"done": True}
```

The runner inspects the `run` signature and only passes `ctx` when
the tool declares it — existing tools that ignore the context
continue to work unchanged.

## Batch tracer event

`AsyncParallelToolRunner` (and the realtime broker) emit a
`ToolBatchTracerEvent` alongside the per-call `ToolCallTracerEvent`s,
so observers can measure parallelism gains:

```python
from mojentic.tracer import TracerSystem
from mojentic.tracer.tracer_events import ToolBatchTracerEvent

tracer = TracerSystem()
broker = RealtimeVoiceBroker(..., tracer=tracer)
...
for batch in tracer.get_events(event_type=ToolBatchTracerEvent):
    print(
        f"{len(batch.tool_names)} tools — {batch.call_duration_ms:.0f}ms "
        f"({batch.success_count}/{len(batch.tool_names)} ok)"
    )
```
