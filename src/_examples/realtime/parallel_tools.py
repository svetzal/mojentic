"""
Realtime parallel tool execution demo.

Three tools are exposed; the prompt is crafted to make the model
invoke all three. The :class:`AsyncParallelToolRunner` (default for
the realtime broker) dispatches them concurrently. The example prints
the per-batch tracer event to make the speed-up observable.
"""
import asyncio
import os
import sys

from mojentic.llm.tools.current_datetime import CurrentDateTimeTool
from mojentic.llm.tools.date_resolver import ResolveDateTool
from mojentic.llm.tools.llm_tool import LLMTool
from mojentic.realtime import (
    OpenAIRealtimeGateway,
    RealtimeVoiceBroker,
    RealtimeVoiceConfig,
)
from mojentic.tracer import TracerSystem
from mojentic.tracer.tracer_events import ToolBatchTracerEvent


class _AddTool(LLMTool):
    def run(self, a: float = 0, b: float = 0) -> dict:
        return {"sum": a + b}

    @property
    def descriptor(self):
        return {
            "type": "function",
            "function": {
                "name": "add",
                "description": "Add two numbers and return the sum.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "a": {"type": "number"},
                        "b": {"type": "number"},
                    },
                    "required": ["a", "b"],
                },
            },
        }


async def main() -> None:
    if not os.environ.get("OPENAI_API_KEY"):
        print("Set OPENAI_API_KEY to run this example.", file=sys.stderr)
        return

    tracer = TracerSystem()
    broker = RealtimeVoiceBroker(
        model="gpt-realtime",
        gateway=OpenAIRealtimeGateway(),
        config=RealtimeVoiceConfig(
            modalities=["text"],
            instructions=(
                "You have access to tools. When asked multiple sub-questions, "
                "call ALL relevant tools in one turn instead of asking one at a time."
            ),
            turn_detection="none",
            input_audio_transcription=False,
            tools=[CurrentDateTimeTool(), ResolveDateTool(), _AddTool()],
        ),
        tracer=tracer,
    )

    session = await broker.connect()
    try:
        await session.send_text(
            "I need three things at once: the current datetime, what date "
            "'next friday' falls on, and 47 + 19."
        )
        async for event in session.events():
            if event.kind == "tool_call_dispatched":
                print(f"[tool] {event.name}({event.args})")
            elif event.kind == "tool_call_completed":
                print(f"[tool] {event.name} → {event.result}")
            elif event.kind == "assistant_text_delta":
                print(event.delta, end="", flush=True)
            elif event.kind == "assistant_turn_completed":
                print()
                # After both turns (tools + final) we're done.
                batches = tracer.get_events(event_type=ToolBatchTracerEvent)
                if batches:
                    last = batches[-1]
                    print(
                        f"\n[batch] {len(last.tool_names)} tools in "
                        f"{last.call_duration_ms:.0f}ms wall-clock; "
                        f"{last.success_count} ok / {last.failure_count} failed"
                    )
                    break
            elif event.kind == "error":
                print(f"[error] {event.error}", file=sys.stderr)
                break
    finally:
        await session.close()


if __name__ == "__main__":
    asyncio.run(main())
