"""
Pydantic validators for OpenAI Realtime API events.

These validate event shape at the gateway boundary. Unknown fields are
allowed (Pydantic ``extra='allow'``) so provider drift doesn't crash
parsing — only the fields the broker actually consumes are validated.
Use ``raw_events()`` on the session for fields outside this schema.

Schema snapshot: OpenAI Realtime API beta circa 2026-05.
"""
from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, ValidationError


class _PassthroughModel(BaseModel):
    model_config = ConfigDict(extra="allow")


class SessionCreated(_PassthroughModel):
    type: Literal["session.created"]
    session: Dict[str, Any]


class SessionUpdated(_PassthroughModel):
    type: Literal["session.updated"]
    session: Dict[str, Any]


class SpeechStarted(_PassthroughModel):
    type: Literal["input_audio_buffer.speech_started"]
    audio_start_ms: Optional[int] = None
    item_id: Optional[str] = None


class SpeechStopped(_PassthroughModel):
    type: Literal["input_audio_buffer.speech_stopped"]
    audio_end_ms: Optional[int] = None
    item_id: Optional[str] = None


class InputTranscriptionCompleted(_PassthroughModel):
    type: Literal["conversation.item.input_audio_transcription.completed"]
    item_id: str
    transcript: str


class InputTranscriptionDelta(_PassthroughModel):
    type: Literal["conversation.item.input_audio_transcription.delta"]
    item_id: str
    delta: str


class ResponseCreated(_PassthroughModel):
    type: Literal["response.created"]
    response: Dict[str, Any]


class ResponseDone(_PassthroughModel):
    type: Literal["response.done"]
    response: Dict[str, Any]


class OutputItemAdded(_PassthroughModel):
    type: Literal["response.output_item.added"]
    response_id: str
    output_index: Optional[int] = None
    item: Dict[str, Any]


class OutputItemDone(_PassthroughModel):
    type: Literal["response.output_item.done"]
    response_id: str
    item: Dict[str, Any]


class AudioDelta(_PassthroughModel):
    """Either ``response.audio.delta`` or ``response.output_audio.delta``."""

    type: Literal["response.audio.delta", "response.output_audio.delta"]
    response_id: str
    item_id: Optional[str] = None
    delta: str


class AudioTranscriptDelta(_PassthroughModel):
    type: Literal[
        "response.audio_transcript.delta",
        "response.output_audio_transcript.delta",
    ]
    response_id: str
    item_id: Optional[str] = None
    delta: str


class AudioTranscriptDone(_PassthroughModel):
    type: Literal[
        "response.audio_transcript.done",
        "response.output_audio_transcript.done",
    ]
    response_id: str
    item_id: Optional[str] = None
    transcript: str


class TextDelta(_PassthroughModel):
    type: Literal["response.text.delta", "response.output_text.delta"]
    response_id: str
    item_id: Optional[str] = None
    delta: str


class TextDone(_PassthroughModel):
    type: Literal["response.text.done", "response.output_text.done"]
    response_id: str
    item_id: Optional[str] = None
    text: str


class FunctionCallArgsDelta(_PassthroughModel):
    type: Literal["response.function_call_arguments.delta"]
    response_id: str
    item_id: Optional[str] = None
    call_id: str
    delta: str


class FunctionCallArgsDone(_PassthroughModel):
    type: Literal["response.function_call_arguments.done"]
    response_id: str
    item_id: Optional[str] = None
    call_id: str
    name: str
    arguments: str


class RateLimitsUpdated(_PassthroughModel):
    type: Literal["rate_limits.updated"]
    rate_limits: List[Dict[str, Any]]


class ServerErrorEvent(_PassthroughModel):
    type: Literal["error"]
    error: Dict[str, Any]


_SCHEMA_REGISTRY = {
    "session.created": SessionCreated,
    "session.updated": SessionUpdated,
    "input_audio_buffer.speech_started": SpeechStarted,
    "input_audio_buffer.speech_stopped": SpeechStopped,
    "conversation.item.input_audio_transcription.completed": InputTranscriptionCompleted,
    "conversation.item.input_audio_transcription.delta": InputTranscriptionDelta,
    "response.created": ResponseCreated,
    "response.done": ResponseDone,
    "response.output_item.added": OutputItemAdded,
    "response.output_item.done": OutputItemDone,
    "response.audio.delta": AudioDelta,
    "response.output_audio.delta": AudioDelta,
    "response.audio_transcript.delta": AudioTranscriptDelta,
    "response.output_audio_transcript.delta": AudioTranscriptDelta,
    "response.audio_transcript.done": AudioTranscriptDone,
    "response.output_audio_transcript.done": AudioTranscriptDone,
    "response.text.delta": TextDelta,
    "response.output_text.delta": TextDelta,
    "response.text.done": TextDone,
    "response.output_text.done": TextDone,
    "response.function_call_arguments.delta": FunctionCallArgsDelta,
    "response.function_call_arguments.done": FunctionCallArgsDone,
    "rate_limits.updated": RateLimitsUpdated,
    "error": ServerErrorEvent,
}


class RawServerEvent(BaseModel):
    """Fallback wrapper for server events outside the known registry."""

    model_config = ConfigDict(extra="allow")
    type: str = Field(...)


def parse_server_event(raw: Any) -> Dict[str, Any]:
    """
    Best-effort parse: returns the validated event as a dict when
    recognised, otherwise the raw payload so callers can still surface
    it through ``raw_events()``.

    A malformed payload (no ``type``) becomes ``{"type": "unknown"}``.
    """
    if not isinstance(raw, dict) or "type" not in raw:
        return {"type": "unknown"}

    event_type = raw.get("type")
    schema = _SCHEMA_REGISTRY.get(event_type)
    if schema is None:
        return raw
    try:
        return schema.model_validate(raw).model_dump()
    except ValidationError:
        # Fall back to the raw payload — boundary validation is best-effort
        # so provider drift never crashes parsing.
        return raw
