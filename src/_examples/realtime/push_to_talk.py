"""
Push-to-talk realtime example.

Uses ``turn_detection='none'`` so the client (not the server's VAD)
decides when a user turn is complete. The example reads a WAV file
from disk as the user's audio input, commits manually, and prints the
streamed assistant transcript.

Generate or supply ``./input.wav`` (24kHz, mono, 16-bit PCM) before
running.
"""
import asyncio
import os
import sys
import wave
from typing import AsyncIterator

import numpy as np

from mojentic.realtime import (
    OpenAIRealtimeGateway,
    RealtimeVoiceBroker,
    RealtimeVoiceConfig,
    ServerVadConfig,
)


CHUNK_FRAMES = 2400  # 100ms at 24kHz


async def wav_frames(path: str) -> AsyncIterator[np.ndarray]:
    """Yield PCM16 frames from a 24 kHz mono WAV file."""
    with wave.open(path, "rb") as wav:
        if wav.getframerate() != 24000 or wav.getnchannels() != 1 or wav.getsampwidth() != 2:
            raise ValueError("input WAV must be 24kHz mono 16-bit PCM")
        while True:
            raw = wav.readframes(CHUNK_FRAMES)
            if not raw:
                return
            yield np.frombuffer(raw, dtype="<i2").copy()
            # Pace the iteration so the server's buffer doesn't bloat.
            await asyncio.sleep(CHUNK_FRAMES / 24000)


async def main() -> None:
    if not os.environ.get("OPENAI_API_KEY"):
        print("Set OPENAI_API_KEY to run this example.", file=sys.stderr)
        return
    input_path = os.environ.get("REALTIME_INPUT_WAV", "input.wav")
    if not os.path.exists(input_path):
        print(
            f"Missing {input_path!r}. Set REALTIME_INPUT_WAV to a 24kHz mono "
            "16-bit PCM WAV file path.",
            file=sys.stderr,
        )
        return

    broker = RealtimeVoiceBroker(
        model="gpt-realtime",
        gateway=OpenAIRealtimeGateway(),
        config=RealtimeVoiceConfig(
            modalities=["audio", "text"],
            voice="verse",
            turn_detection="none",  # we commit manually
            # Disable in-band transcription; rely on streaming transcript deltas.
            input_audio_transcription=False,
            # Make sure interrupted responses honour the default 'drop' policy.
            on_interrupt="drop",
        ),
    )
    # Silence the unused-import warning while keeping the symbol importable.
    _ = ServerVadConfig

    session = await broker.connect()
    try:
        # Stream the WAV file in.
        await session.send_audio(wav_frames(input_path))
        # Commit and ask for a response.
        await session.commit_audio()
        async for event in session.events():
            if event.kind == "assistant_transcript_delta":
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
