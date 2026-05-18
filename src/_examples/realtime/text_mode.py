"""
Realtime text-mode hello world.

Connects to OpenAI's Realtime API and exchanges a single text turn —
no audio device required, runs anywhere. Useful as a first-touch
example and as a smoke test that the websocket plumbing works.

Run:

    OPENAI_API_KEY=... uv run python src/_examples/realtime/text_mode.py
"""
import asyncio
import os
import sys

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
            instructions="You are a concise assistant. Answer in one sentence.",
            turn_detection="none",
            input_audio_transcription=False,
        ),
    )

    session = await broker.connect()
    try:
        await session.send_text("What's the capital of Canada?")
        async for event in session.events():
            if event.kind == "assistant_text_delta":
                print(event.delta, end="", flush=True)
            elif event.kind == "assistant_turn_completed":
                print()
                break
            elif event.kind == "error":
                print(f"[error] {event.error}", file=sys.stderr)
                break
    finally:
        await session.close()


if __name__ == "__main__":
    asyncio.run(main())
