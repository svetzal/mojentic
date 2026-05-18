# Realtime Voice

Mojentic ships a `RealtimeVoiceBroker` sibling to `LLMBroker` for
duplex voice + tool sessions against realtime-capable providers
(currently OpenAI's Realtime API over WebSocket).

The realtime broker speaks the same vendor-neutral surface as the
TypeScript port in `mojentic-ts`: an async event stream, parallel
tool calls, interruption / barge-in, and a tracer hook for batch
parallelism.

## 30-second example (text mode)

Text mode needs no audio device, so it runs anywhere.

```python
import asyncio

from mojentic.realtime import (
    OpenAIRealtimeGateway,
    RealtimeVoiceBroker,
    RealtimeVoiceConfig,
)


async def main() -> None:
    broker = RealtimeVoiceBroker(
        model="gpt-realtime",
        gateway=OpenAIRealtimeGateway(),
        config=RealtimeVoiceConfig(
            modalities=["text"],
            instructions="You are a concise assistant.",
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
    finally:
        await session.close()


asyncio.run(main())
```

## Tools work unchanged

Pass any `LLMTool` to `RealtimeVoiceConfig.tools`. The broker
dispatches them via `AsyncParallelToolRunner` by default — when the
model emits multiple `function_call` items in one turn, they run
concurrently and the results are batched back as
`function_call_output` items before the next `response.create` lands.

```python
from mojentic.llm.tools.current_datetime import CurrentDateTimeTool
from mojentic.llm.tools.date_resolver import ResolveDateTool

broker = RealtimeVoiceBroker(
    model="gpt-realtime",
    gateway=OpenAIRealtimeGateway(),
    config=RealtimeVoiceConfig(
        tools=[CurrentDateTimeTool(), ResolveDateTool()],
        modalities=["text"],
        turn_detection="none",
    ),
)
```

## Audio I/O

The library is **hardware-free**: no `sounddevice` / `pyaudio`
dependencies in the package. Audio I/O is plumbed via async
iterables of PCM16 frames (numpy `int16` arrays, 24 kHz mono).

For portable examples, use WAV file I/O — see
`src/_examples/realtime/simple_voice_wav.py`. For live device I/O,
integrate `sounddevice` (or your platform's audio library) at the
boundary; the realtime session API stays the same.

```python
async def wav_frames(path):
    import wave, numpy as np
    with wave.open(path, "rb") as wav:
        while True:
            raw = wav.readframes(2400)
            if not raw:
                return
            yield np.frombuffer(raw, dtype="<i2").copy()

await session.send_audio(wav_frames("input.wav"))
async for pcm in session.audio_output():
    ...  # write to file, speaker, etc.
```

## Events

The session exposes a vendor-neutral discriminated union, keyed on
`kind`. Pattern match in `match`/`if` chains:

| Group | Kinds |
|---|---|
| Session lifecycle | `session_opened`, `session_updated`, `session_closed` |
| User speech | `user_speech_started`, `user_speech_stopped`, `user_transcript_delta`, `user_transcript` |
| Assistant output | `assistant_turn_started`, `assistant_text_delta`, `assistant_text`, `assistant_transcript_delta`, `assistant_transcript`, `assistant_audio_delta`, `assistant_turn_completed` |
| Tool calls | `tool_call_started`, `tool_call_args_delta`, `tool_call_dispatched`, `tool_call_completed`, `tool_call_failed`, `tool_batch_submitted` |
| Control | `interrupted`, `rate_limited`, `error` |

If you need raw gateway events (every field OpenAI emits, including
ones the broker doesn't normalise), iterate `session.raw_events()`.

## Interruption

Either of these cancels the in-flight assistant response and aborts
in-flight tool execution:

- The server fires `input_audio_buffer.speech_started` while a
  response is mid-flight (barge-in).
- The client calls `await session.interrupt()`.

The `on_interrupt` config knob decides what happens to tool outputs
already in flight when the cancel lands:

| Policy | Behaviour |
|---|---|
| `drop` (default) | Discard outputs from the cancelled batch. Stale answers don't pollute the next turn. |
| `submit-completed-only` | Submit outputs that finished before the abort signal; drop the in-flight ones. |
| `submit` | Submit every outcome, even after the model started a new turn. |

Async tools that observe `ctx.cancel_event` can hard-cancel themselves
when an interrupt lands; tools that ignore the context simply finish
and their outputs are dropped (under `drop`).

## Tracing

Pass a `TracerSystem` to the broker to get per-call
`ToolCallTracerEvent`s and per-batch `ToolBatchTracerEvent`s:

```python
from mojentic.tracer import TracerSystem
from mojentic.tracer.tracer_events import ToolBatchTracerEvent

tracer = TracerSystem()
broker = RealtimeVoiceBroker(..., tracer=tracer)
...
for batch in tracer.get_events(event_type=ToolBatchTracerEvent):
    print(batch.printable_summary())
```

## Lifecycle and cleanup

`RealtimeSession` works as an async context manager:

```python
async with await broker.connect() as session:
    ...
# session.close() is called automatically on exit
```

`close()` is idempotent. It cancels any in-flight tool batch, sends
`response.cancel` if a response is mid-flight, then closes the
underlying socket and ends all event streams.
