"""
Realtime tool calling — single tool.

Exposes :class:`CurrentDateTimeTool` to the model and observes it being
invoked automatically as part of a text-mode turn. Demonstrates that
existing Mojentic tools work unchanged in the realtime broker.
"""
import asyncio
import os
import sys

from mojentic.llm.tools.current_datetime import CurrentDateTimeTool
from mojentic.realtime import (
    OpenAIRealtimeGateway,
    RealtimeVoiceBroker,
    RealtimeVoiceConfig,
)


async def main() -> None:
    if not os.environ.get("OPENAI_API_KEY"):
        print("Set OPENAI_API_KEY to run this example.", file=sys.stderr)
        return

    broker = RealtimeVoiceBroker(
        model="gpt-realtime",
        gateway=OpenAIRealtimeGateway(),
        config=RealtimeVoiceConfig(
            modalities=["text"],
            instructions=(
                "You have access to tools. Use them as needed and answer "
                "concisely."
            ),
            turn_detection="none",
            input_audio_transcription=False,
            tools=[CurrentDateTimeTool()],
        ),
    )

    session = await broker.connect()
    try:
        await session.send_text("What time is it right now?")
        async for event in session.events():
            if event.kind == "tool_call_dispatched":
                print(f"[tool] {event.name}({event.args})")
            elif event.kind == "tool_call_completed":
                print(f"[tool] {event.name} → {event.result}")
            elif event.kind == "assistant_text_delta":
                print(event.delta, end="", flush=True)
            elif event.kind == "assistant_turn_completed":
                print()
            elif event.kind == "error":
                print(f"[error] {event.error}", file=sys.stderr)
                break
            # End once we have at least one assistant turn after the tool call.
            if event.kind == "assistant_turn_completed" and any(
                True for _ in [None]
            ):
                # naive single-turn termination
                break
    finally:
        await session.close()


if __name__ == "__main__":
    asyncio.run(main())
