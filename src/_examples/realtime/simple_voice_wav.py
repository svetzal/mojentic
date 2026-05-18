"""
Simple voice round-trip using WAV files for I/O.

Reads ``input.wav`` (24 kHz mono 16-bit PCM) as user audio, writes
the streamed assistant audio to ``output.wav``. Hardware-free so the
example works on macOS / Linux / Windows / CI without any platform
device libraries.

Run:

    OPENAI_API_KEY=... uv run python src/_examples/realtime/simple_voice_wav.py

For platform audio device support, integrate a library such as
``sounddevice`` or ``pyaudio`` at the boundaries; the realtime
session interface stays the same.
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
)


CHUNK_FRAMES = 2400  # 100ms at 24kHz


async def wav_frames(path: str) -> AsyncIterator[np.ndarray]:
    with wave.open(path, "rb") as wav:
        if wav.getframerate() != 24000 or wav.getnchannels() != 1 or wav.getsampwidth() != 2:
            raise ValueError("input WAV must be 24kHz mono 16-bit PCM")
        while True:
            raw = wav.readframes(CHUNK_FRAMES)
            if not raw:
                return
            yield np.frombuffer(raw, dtype="<i2").copy()
            await asyncio.sleep(CHUNK_FRAMES / 24000)


async def main() -> None:
    if not os.environ.get("OPENAI_API_KEY"):
        print("Set OPENAI_API_KEY to run this example.", file=sys.stderr)
        return
    input_path = os.environ.get("REALTIME_INPUT_WAV", "input.wav")
    output_path = os.environ.get("REALTIME_OUTPUT_WAV", "output.wav")
    if not os.path.exists(input_path):
        print(f"Missing {input_path!r}.", file=sys.stderr)
        return

    broker = RealtimeVoiceBroker(
        model="gpt-realtime",
        gateway=OpenAIRealtimeGateway(),
        config=RealtimeVoiceConfig(
            modalities=["audio", "text"],
            voice="verse",
            turn_detection="server_vad",
        ),
    )

    session = await broker.connect()
    try:
        with wave.open(output_path, "wb") as out:
            out.setnchannels(1)
            out.setsampwidth(2)
            out.setframerate(24000)

            async def writer():
                async for pcm in session.audio_output():
                    out.writeframes(pcm.tobytes())

            writer_task = asyncio.create_task(writer())

            await session.send_audio(wav_frames(input_path))

            async for event in session.events():
                if event.kind == "assistant_turn_completed":
                    break
                if event.kind == "error":
                    print(f"[error] {event.error}", file=sys.stderr)
                    break

            await session.close()
            await writer_task

        print(f"Wrote assistant audio to {output_path}")
    finally:
        await session.close()


if __name__ == "__main__":
    asyncio.run(main())
