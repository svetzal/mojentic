"""
Realtime interruption / barge-in demo.

Starts an assistant turn that will take a while, then manually
interrupts it. The session emits an ``InterruptedEvent`` and sends a
``response.cancel`` to the gateway. Outputs from any in-flight tool
calls are dropped per the default ``on_interrupt='drop'`` policy.
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
            instructions=(
                "You are a long-winded storyteller. "
                "When asked for a story, take your time and elaborate."
            ),
            turn_detection="none",
            input_audio_transcription=False,
            on_interrupt="drop",
        ),
    )

    session = await broker.connect()
    try:
        await session.send_text("Tell me a long story about a wise old turtle.")

        async def interrupter():
            await asyncio.sleep(2.0)
            print("\n[interrupt] ...nope, never mind.")
            await session.interrupt()

        interrupt_task = asyncio.create_task(interrupter())

        async for event in session.events():
            if event.kind == "assistant_text_delta":
                print(event.delta, end="", flush=True)
            elif event.kind == "interrupted":
                print(f"\n[interrupted] reason={event.reason}")
                break
            elif event.kind == "error":
                print(f"\n[error] {event.error}", file=sys.stderr)
                break

        await interrupt_task
    finally:
        await session.close()


if __name__ == "__main__":
    asyncio.run(main())
