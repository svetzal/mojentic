"""
Realtime session — the stateful surface exposed by
:class:`mojentic.realtime.broker.RealtimeVoiceBroker`.

Owns the gateway-session lifetime, demultiplexes raw OpenAI events into
a vendor-neutral :data:`RealtimeEvent` stream, and drives parallel tool
execution per response turn.
"""
from __future__ import annotations

import asyncio
import json
import time
import uuid
from typing import Any, AsyncIterator, Dict, List, Optional

import numpy as np
import structlog

from mojentic.llm.tools.llm_tool import LLMTool
from mojentic.llm.tools.runner import (
    AsyncParallelToolRunner,
    ToolCallExecution,
    ToolCallOutcome,
    ToolRunContext,
    ToolRunner,
)
from mojentic.realtime.codec import decode_base64_pcm16, encode_base64_pcm16
from mojentic.realtime.config import (
    REALTIME_DEFAULTS,
    InputAudioTranscriptionConfig,
    RealtimeToolChoice,
    RealtimeToolChoiceFunction,
    RealtimeVoiceConfig,
    SemanticVadConfig,
    ServerVadConfig,
    TurnDetectionMode,
)
from mojentic.realtime.events import (
    AssistantAudioDeltaEvent,
    AssistantTextDeltaEvent,
    AssistantTextEvent,
    AssistantTranscriptDeltaEvent,
    AssistantTranscriptEvent,
    AssistantTurnCompletedEvent,
    AssistantTurnStartedEvent,
    ErrorEvent,
    InterruptedEvent,
    RateLimitedEvent,
    RealtimeEvent,
    SessionClosedEvent,
    SessionOpenedEvent,
    SessionUpdatedEvent,
    TokenUsage,
    ToolBatchSubmittedEvent,
    ToolCallArgsDeltaEvent,
    ToolCallCompletedEvent,
    ToolCallDispatchedEvent,
    ToolCallFailedEvent,
    ToolCallStartedEvent,
    UserSpeechStartedEvent,
    UserSpeechStoppedEvent,
    UserTranscriptDeltaEvent,
    UserTranscriptEvent,
)
from mojentic.realtime.gateway import RealtimeGatewaySession
from mojentic.tracer.tracer_system import TracerSystem

logger = structlog.get_logger()

TOOL_BATCH_SOURCE = "RealtimeVoiceBroker"

_EOS = object()


# -----------------------------------------------------------------------------
# session.update payload builder (pure function, mirrors TS)
# -----------------------------------------------------------------------------


def _encode_audio_format(fmt: str) -> Dict[str, Any]:
    if fmt == "pcm16":
        return {"type": "audio/pcm", "rate": 24000}
    if fmt == "g711_ulaw":
        return {"type": "audio/pcmu"}
    if fmt == "g711_alaw":
        return {"type": "audio/pcma"}
    raise ValueError(f"Unsupported audio format: {fmt!r}")


def _strip_none(obj: Dict[str, Any]) -> Dict[str, Any]:
    return {k: v for k, v in obj.items() if v is not None}


def _encode_turn_detection(td: TurnDetectionMode) -> Optional[Dict[str, Any]]:
    if td == "none":
        return None
    if td == "server_vad":
        return {"type": "server_vad"}
    if td == "semantic_vad":
        return {"type": "semantic_vad"}
    if isinstance(td, SemanticVadConfig):
        return _strip_none({
            "type": "semantic_vad",
            "eagerness": td.eagerness,
            "create_response": td.create_response,
            "interrupt_response": td.interrupt_response,
        })
    if isinstance(td, ServerVadConfig):
        return _strip_none({
            "type": "server_vad",
            "threshold": td.threshold,
            "prefix_padding_ms": td.prefix_padding_ms,
            "silence_duration_ms": td.silence_duration_ms,
            "create_response": td.create_response,
            "interrupt_response": td.interrupt_response,
            "idle_timeout_ms": td.idle_timeout_ms,
        })
    raise ValueError(f"Unsupported turn_detection mode: {td!r}")


def _encode_tool_choice(choice: Optional[RealtimeToolChoice]) -> Any:
    if choice is None:
        return "auto"
    if isinstance(choice, str):
        return choice
    if isinstance(choice, RealtimeToolChoiceFunction):
        return {"type": "function", "name": choice.name}
    raise ValueError(f"Unsupported tool_choice: {choice!r}")


def build_session_update(config: RealtimeVoiceConfig) -> Dict[str, Any]:
    """
    Build a vendor-specific ``session.update`` payload from the
    vendor-neutral config, matching the OpenAI Realtime GA shape.

    GA specifics:
    - ``session.type: 'realtime'`` is required.
    - ``modalities`` maps to GA ``output_modalities`` (output-only).
    - Voice + output audio format live under ``session.audio.output``.
    - Turn detection, transcription, and input audio format live under
      ``session.audio.input``.
    - ``temperature`` is no longer accepted on GA — silently dropped.
    - ``max_response_output_tokens`` maps to ``max_output_tokens``.
    """
    modalities = config.modalities or list(REALTIME_DEFAULTS.modalities)
    turn_detection = config.turn_detection or REALTIME_DEFAULTS.turn_detection

    output_modalities = ["audio"] if "audio" in modalities else ["text"]

    audio_input: Dict[str, Any] = {
        "format": _encode_audio_format(
            config.input_audio_format or REALTIME_DEFAULTS.input_audio_format
        ),
        "turn_detection": _encode_turn_detection(turn_detection),
    }
    if config.input_audio_transcription is False:
        audio_input["transcription"] = None
    elif isinstance(config.input_audio_transcription, InputAudioTranscriptionConfig):
        audio_input["transcription"] = config.input_audio_transcription.model_dump()

    audio_output: Dict[str, Any] = {
        "format": _encode_audio_format(
            config.output_audio_format or REALTIME_DEFAULTS.output_audio_format
        ),
    }
    if config.voice is not None:
        audio_output["voice"] = config.voice

    session: Dict[str, Any] = {
        "type": "realtime",
        "output_modalities": output_modalities,
        "audio": {"input": audio_input, "output": audio_output},
        "tool_choice": _encode_tool_choice(config.tool_choice or REALTIME_DEFAULTS.tool_choice),
    }

    if config.instructions is not None:
        session["instructions"] = config.instructions
    if config.max_response_output_tokens is not None:
        session["max_output_tokens"] = config.max_response_output_tokens
    if config.tools:
        session["tools"] = [
            {
                "type": "function",
                "name": tool.descriptor["function"]["name"],
                "description": tool.descriptor["function"]["description"],
                "parameters": tool.descriptor["function"]["parameters"],
            }
            for tool in config.tools
        ]
    if config.provider_extras:
        session.update(config.provider_extras)

    return {"type": "session.update", "session": session}


# -----------------------------------------------------------------------------
# Per-turn state
# -----------------------------------------------------------------------------


class _PendingCall:
    __slots__ = ("call_id", "item_id", "name", "args_buffer", "parsed_args", "done")

    def __init__(self, call_id: str, name: str, item_id: Optional[str] = None):
        self.call_id = call_id
        self.item_id = item_id
        self.name = name
        self.args_buffer: str = ""
        self.parsed_args: Optional[Dict[str, Any]] = None
        self.done: bool = False


class _TurnState:
    __slots__ = (
        "turn_id",
        "calls",
        "text_buffer",
        "transcript_buffer",
        "cancelled",
        "cancel_event",
    )

    def __init__(self, turn_id: str):
        self.turn_id = turn_id
        self.calls: Dict[str, _PendingCall] = {}
        self.text_buffer: str = ""
        self.transcript_buffer: str = ""
        self.cancelled: bool = False
        self.cancel_event: asyncio.Event = asyncio.Event()


# -----------------------------------------------------------------------------
# RealtimeSession
# -----------------------------------------------------------------------------


class RealtimeSession:
    """
    Stateful realtime session handle.

    Constructed by :class:`RealtimeVoiceBroker`; users don't instantiate
    this directly. Use as an async context manager (``async with``) for
    deterministic close-on-exit.
    """

    def __init__(
        self,
        gateway_session: RealtimeGatewaySession,
        config: RealtimeVoiceConfig,
        tool_runner: Optional[ToolRunner] = None,
        tracer: Optional[TracerSystem] = None,
        correlation_id: Optional[str] = None,
    ):
        self._gateway_session = gateway_session
        self._config = config
        self._tools: List[LLMTool] = list(config.tools or [])
        self._tool_runner: ToolRunner = tool_runner or AsyncParallelToolRunner()
        self._tracer = tracer
        self._correlation_id = correlation_id or str(uuid.uuid4())
        self._current_instructions = config.instructions

        self._normalized_queue: asyncio.Queue = asyncio.Queue()
        self._raw_queue: asyncio.Queue = asyncio.Queue()
        self._audio_queue: asyncio.Queue = asyncio.Queue()

        self._current_turn: Optional[_TurnState] = None
        self._current_response_id: Optional[str] = None
        self._pending_batches: set = set()
        self._closed = False

        self._emit(SessionOpenedEvent(session_id=gateway_session.session_id))
        self._pump_task = asyncio.create_task(self._pump(), name="realtime-session-pump")

    # ------------------------------------------------------------------ public

    async def __aenter__(self) -> "RealtimeSession":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        await self.close()

    async def initialise(self) -> None:
        """Send the initial ``session.update``. The broker calls this."""
        payload = build_session_update(self._config)
        await self._gateway_session.send_event(payload)

    async def events(self) -> AsyncIterator[RealtimeEvent]:
        """Vendor-neutral event stream. Terminates when the session closes."""
        while True:
            item = await self._normalized_queue.get()
            if item is _EOS:
                return
            yield item

    async def raw_events(self) -> AsyncIterator[Dict[str, Any]]:
        """Raw gateway events for power users / debugging."""
        while True:
            item = await self._raw_queue.get()
            if item is _EOS:
                return
            yield item

    async def audio_output(self) -> AsyncIterator[np.ndarray]:
        """Async generator yielding PCM frames from the assistant."""
        while True:
            item = await self._audio_queue.get()
            if item is _EOS:
                return
            yield item

    async def send_text(self, text: str) -> None:
        """Send a text-mode user message and request a response."""
        await self._gateway_session.send_event({
            "type": "conversation.item.create",
            "item": {
                "type": "message",
                "role": "user",
                "content": [{"type": "input_text", "text": text}],
            },
        })
        await self._gateway_session.send_event({"type": "response.create"})

    async def send_audio(self, stream) -> None:
        """
        Pipe an async iterable of PCM frames into the input audio buffer.

        Frames may be :class:`numpy.ndarray` (int16) or raw bytes
        already in PCM16 wire format. The codec is applied transparently.
        Returns once the iterable completes or the session closes.
        """
        async for frame in stream:
            if self._closed:
                return
            await self._gateway_session.send_event({
                "type": "input_audio_buffer.append",
                "audio": encode_base64_pcm16(frame),
            })

    async def commit_audio(self) -> None:
        """
        Manually commit the input audio buffer (only meaningful with
        ``turn_detection='none'``) and request a response.
        """
        await self._gateway_session.send_event({"type": "input_audio_buffer.commit"})
        await self._gateway_session.send_event({"type": "response.create"})

    async def interrupt(self) -> None:
        """Manually cancel the in-flight response and abort tool execution."""
        await self._cancel_current_turn("manual")

    async def update_instructions(self, instructions: str) -> None:
        """Hot-update assistant instructions mid-session."""
        self._current_instructions = instructions
        await self._gateway_session.send_event({
            "type": "session.update",
            "session": {"instructions": instructions},
        })

    async def close(self) -> None:
        """Close the session, dispose the socket, and end all event streams."""
        if self._closed:
            return
        self._closed = True
        if self._current_turn is not None and not self._current_turn.cancelled:
            self._current_turn.cancelled = True
            self._current_turn.cancel_event.set()
        if self._pending_batches:
            await asyncio.gather(*self._pending_batches, return_exceptions=True)
        await self._gateway_session.close()
        self._emit(SessionClosedEvent(reason="client"))
        self._end_channels()
        self._pump_task.cancel()
        try:
            await self._pump_task
        except (asyncio.CancelledError, Exception):  # noqa: BLE001
            pass

    def get_instructions(self) -> Optional[str]:
        """Effective instructions from the most recent ``session.update``."""
        return self._current_instructions

    # ------------------------------------------------------------------ helpers

    def _emit(self, event: RealtimeEvent) -> None:
        try:
            self._normalized_queue.put_nowait(event)
        except asyncio.QueueFull:  # pragma: no cover
            logger.warning("normalized queue full; dropping event", kind=event.kind)

    def _end_channels(self) -> None:
        self._normalized_queue.put_nowait(_EOS)
        self._raw_queue.put_nowait(_EOS)
        self._audio_queue.put_nowait(_EOS)

    # ------------------------------------------------------------------ pump

    async def _pump(self) -> None:
        try:
            async for raw in self._gateway_session.events():
                self._raw_queue.put_nowait(raw)
                await self._handle_server_event(raw)
                if self._closed:
                    break
        except asyncio.CancelledError:
            raise
        except Exception as err:  # noqa: BLE001
            self._emit(ErrorEvent(error=err, recoverable=False))
        finally:
            if not self._closed:
                self._emit(SessionClosedEvent(reason="server"))
                self._end_channels()
                self._closed = True

    async def _handle_server_event(self, raw: Dict[str, Any]) -> None:
        event_type = raw.get("type")
        # Dispatch via a small if-elif chain — match/case keeps this readable
        # but pyflakes complains about the discriminant; if/elif is fine here.
        if event_type == "session.created":
            return  # session_opened already emitted on construction
        if event_type == "session.updated":
            self._emit(SessionUpdatedEvent(
                config={"instructions": self._current_instructions}
            ))
            return
        if event_type == "input_audio_buffer.speech_started":
            self._emit(UserSpeechStartedEvent(
                at_ms=int(raw.get("audio_start_ms") or _now_ms())
            ))
            if self._current_turn is not None and not self._current_turn.cancelled:
                await self._cancel_current_turn("barge_in")
            return
        if event_type == "input_audio_buffer.speech_stopped":
            self._emit(UserSpeechStoppedEvent(
                at_ms=int(raw.get("audio_end_ms") or _now_ms())
            ))
            return
        if event_type == "conversation.item.input_audio_transcription.delta":
            self._emit(UserTranscriptDeltaEvent(
                item_id=raw["item_id"], delta=raw["delta"]
            ))
            return
        if event_type == "conversation.item.input_audio_transcription.completed":
            self._emit(UserTranscriptEvent(
                item_id=raw["item_id"], text=raw["transcript"]
            ))
            return
        if event_type == "response.created":
            turn_id = raw["response"]["id"]
            self._current_response_id = turn_id
            self._current_turn = _TurnState(turn_id)
            self._emit(AssistantTurnStartedEvent(turn_id=turn_id))
            return
        if event_type == "response.output_item.added":
            item = raw.get("item", {})
            if item.get("type") == "function_call" and item.get("call_id") and item.get("name"):
                turn = self._current_turn
                if turn is None:
                    return
                turn.calls[item["call_id"]] = _PendingCall(
                    call_id=item["call_id"], name=item["name"], item_id=item.get("id")
                )
                self._emit(ToolCallStartedEvent(
                    turn_id=turn.turn_id, call_id=item["call_id"], name=item["name"]
                ))
            return
        if event_type == "response.function_call_arguments.delta":
            call_id = raw["call_id"]
            turn = self._current_turn
            if turn is not None and call_id in turn.calls:
                turn.calls[call_id].args_buffer += raw["delta"]
            self._emit(ToolCallArgsDeltaEvent(call_id=call_id, delta=raw["delta"]))
            return
        if event_type == "response.function_call_arguments.done":
            call_id = raw["call_id"]
            turn = self._current_turn
            if turn is not None and call_id in turn.calls:
                call = turn.calls[call_id]
                call.args_buffer = raw.get("arguments") or call.args_buffer
                call.done = True
            return
        if event_type in ("response.text.delta", "response.output_text.delta"):
            turn = self._current_turn
            if turn is None:
                return
            turn.text_buffer += raw["delta"]
            self._emit(AssistantTextDeltaEvent(turn_id=turn.turn_id, delta=raw["delta"]))
            return
        if event_type in ("response.text.done", "response.output_text.done"):
            turn = self._current_turn
            if turn is None:
                return
            self._emit(AssistantTextEvent(turn_id=turn.turn_id, text=raw["text"]))
            return
        if event_type in ("response.audio_transcript.delta", "response.output_audio_transcript.delta"):
            turn = self._current_turn
            if turn is None:
                return
            turn.transcript_buffer += raw["delta"]
            self._emit(AssistantTranscriptDeltaEvent(
                turn_id=turn.turn_id, delta=raw["delta"]
            ))
            return
        if event_type in ("response.audio_transcript.done", "response.output_audio_transcript.done"):
            turn = self._current_turn
            if turn is None:
                return
            self._emit(AssistantTranscriptEvent(
                turn_id=turn.turn_id, text=raw["transcript"]
            ))
            return
        if event_type in ("response.audio.delta", "response.output_audio.delta"):
            turn = self._current_turn
            if turn is None:
                return
            pcm = decode_base64_pcm16(raw["delta"])
            self._audio_queue.put_nowait(pcm)
            self._emit(AssistantAudioDeltaEvent(turn_id=turn.turn_id, pcm=pcm))
            return
        if event_type == "response.done":
            await self._handle_response_done(raw)
            return
        if event_type == "rate_limits.updated":
            rate_limits = raw.get("rate_limits") or []
            first = rate_limits[0] if rate_limits else {}
            reset_seconds = first.get("reset_seconds") or 0
            self._emit(RateLimitedEvent(
                reset_ms=int(round(reset_seconds * 1000)),
                details={"rate_limits": rate_limits},
            ))
            return
        if event_type == "error":
            err_payload = raw.get("error") or {}
            message = err_payload.get("message", "unknown realtime error")
            # Suppress the expected race when response.cancel lands after the
            # response already completed — common during barge-in.
            if "no active response" in message.lower():
                return
            self._emit(ErrorEvent(
                error=RuntimeError(message),
                recoverable=err_payload.get("type") != "session_error",
            ))
            return
        # Unknown event — only surfaces via raw_events()

    async def _handle_response_done(self, raw: Dict[str, Any]) -> None:
        response = raw.get("response", {})
        turn = self._current_turn
        if turn is None or turn.turn_id != response.get("id"):
            self._current_turn = None
            return

        usage_in = response.get("usage")
        usage_out: Optional[TokenUsage] = None
        if usage_in:
            usage_out = TokenUsage(
                prompt_tokens=usage_in.get("input_tokens"),
                completion_tokens=usage_in.get("output_tokens"),
                total_tokens=usage_in.get("total_tokens"),
                extras={
                    "input_token_details": usage_in.get("input_token_details"),
                    "output_token_details": usage_in.get("output_token_details"),
                },
            )
        self._emit(AssistantTurnCompletedEvent(turn_id=turn.turn_id, usage=usage_out))

        if turn.calls:
            batch_task = asyncio.create_task(
                self._run_tool_batch_for_turn(turn),
                name=f"realtime-tools-{turn.turn_id}",
            )
            self._pending_batches.add(batch_task)
            batch_task.add_done_callback(lambda t, turn=turn: self._finalize_batch(t, turn))
        else:
            self._current_turn = None
            self._current_response_id = None

    def _finalize_batch(self, task: asyncio.Task, turn: _TurnState) -> None:
        self._pending_batches.discard(task)
        if self._current_turn is turn:
            self._current_turn = None
            self._current_response_id = None
        if task.cancelled():
            return
        err = task.exception()
        if err is not None:
            self._emit(ErrorEvent(error=err, recoverable=True))

    async def _run_tool_batch_for_turn(self, turn: _TurnState) -> None:
        executions: List[ToolCallExecution] = []
        for call in turn.calls.values():
            if not call.done and not call.args_buffer:
                continue
            try:
                args = json.loads(call.args_buffer) if call.args_buffer else {}
            except json.JSONDecodeError as err:
                self._emit(ToolCallFailedEvent(call_id=call.call_id, name=call.name, error=err))
                continue
            call.parsed_args = args
            executions.append(ToolCallExecution(id=call.call_id, name=call.name, args=args))

        if not executions:
            return

        batch_start = time.time()

        ctx = ToolRunContext(
            cancel_event=turn.cancel_event,
            correlation_id=self._correlation_id,
            source=TOOL_BATCH_SOURCE,
            on_call_start=lambda call: self._on_tool_call_start(call),
            on_call_complete=lambda outcome: self._on_tool_call_complete(outcome),
        )

        outcomes: List[ToolCallOutcome] = await self._tool_runner.run_batch(
            executions, self._tools, ctx
        )

        if self._tracer is not None:
            ok = sum(1 for o in outcomes if o.ok)
            fail = len(outcomes) - ok
            self._tracer.record_tool_batch(
                batch_id=str(uuid.uuid4()),
                tool_names=[e.name for e in executions],
                success_count=ok,
                failure_count=fail,
                call_duration_ms=(time.time() - batch_start) * 1000.0,
                caller="RealtimeSession.toolBatch",
                source=type(self),
                correlation_id=self._correlation_id,
            )

        policy = self._config.on_interrupt or REALTIME_DEFAULTS.on_interrupt
        to_submit = self._select_outputs_to_submit(turn, outcomes, policy)

        submitted_ids: List[str] = []
        for outcome in to_submit:
            payload = _serialize_outcome(outcome)
            try:
                await self._gateway_session.send_event({
                    "type": "conversation.item.create",
                    "item": {
                        "type": "function_call_output",
                        "call_id": outcome.id,
                        "output": payload,
                    },
                })
                submitted_ids.append(outcome.id)
            except Exception as err:  # noqa: BLE001
                self._emit(ErrorEvent(error=err, recoverable=True))

        if submitted_ids:
            self._emit(ToolBatchSubmittedEvent(turn_id=turn.turn_id, call_ids=submitted_ids))
            await self._gateway_session.send_event({"type": "response.create"})

    def _on_tool_call_start(self, call: ToolCallExecution) -> None:
        self._emit(ToolCallDispatchedEvent(
            call_id=call.id, name=call.name, args=call.args
        ))

    def _on_tool_call_complete(self, outcome: ToolCallOutcome) -> None:
        if self._tracer is not None:
            self._tracer.record_tool_call(
                outcome.name,
                {},  # args attached to ToolCallExecution; we keep tracer simple here
                outcome.result if outcome.ok else {"error": str(outcome.error)},
                caller=TOOL_BATCH_SOURCE,
                call_duration_ms=outcome.duration_ms,
                source=type(self),
                correlation_id=self._correlation_id,
            )
        if outcome.ok:
            self._emit(ToolCallCompletedEvent(
                call_id=outcome.id, name=outcome.name, result=outcome.result
            ))
        else:
            self._emit(ToolCallFailedEvent(
                call_id=outcome.id, name=outcome.name, error=outcome.error
            ))

    @staticmethod
    def _select_outputs_to_submit(
        turn: _TurnState,
        outcomes: List[ToolCallOutcome],
        policy: str,
    ) -> List[ToolCallOutcome]:
        if not turn.cancelled:
            return outcomes
        if policy == "submit":
            return outcomes
        if policy == "drop":
            return []
        return [o for o in outcomes if o.ok]

    async def _cancel_current_turn(self, reason: str) -> None:
        turn = self._current_turn
        if turn is None or turn.cancelled:
            return
        turn.cancelled = True
        turn.cancel_event.set()
        self._emit(InterruptedEvent(turn_id=turn.turn_id, reason=reason))
        if self._current_response_id is not None:
            try:
                await self._gateway_session.send_event({"type": "response.cancel"})
            except Exception as err:  # noqa: BLE001
                self._emit(ErrorEvent(error=err, recoverable=True))


def _serialize_outcome(outcome: ToolCallOutcome) -> str:
    if outcome.ok:
        return _safe_json_dumps(outcome.result)
    return json.dumps({"error": str(outcome.error)})


def _safe_json_dumps(value: Any) -> str:
    if isinstance(value, str):
        return value
    try:
        return json.dumps(value)
    except (TypeError, ValueError) as err:
        return json.dumps({"error": "serialisation_failed", "detail": str(err)})


def _now_ms() -> int:
    return int(time.time() * 1000)
