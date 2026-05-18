"""
Vendor-neutral event union for the realtime subsystem.

Consumers subscribe to this union rather than raw OpenAI events so the
same observer code ports cleanly to other realtime providers and other
Mojentic implementations (TypeScript, Elixir, Rust).
"""
from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional, Union

import numpy as np
from pydantic import BaseModel, ConfigDict, Field


class TokenUsage(BaseModel):
    """Token usage reported when a response turn completes."""

    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None
    total_tokens: Optional[int] = None
    extras: Optional[Dict[str, Any]] = None
    """Provider-specific breakdown (e.g. audio vs text tokens)."""


class RealtimeItem(BaseModel):
    """
    Conversation item in a realtime session.

    Realtime sessions don't map cleanly to chat-completion ``LLMMessage``
    objects because they carry audio, multi-modal content, and tool-call
    lifecycle separate from any single message. A small dedicated shape
    keeps ``LLMMessage`` from getting bent out of shape.
    """

    id: str
    type: Literal["message", "function_call", "function_call_output"]
    role: Optional[Literal["system", "user", "assistant"]] = None
    text: Optional[str] = None
    transcript: Optional[str] = None
    name: Optional[str] = None
    args: Optional[Dict[str, Any]] = None
    output: Optional[Any] = None
    call_id: Optional[str] = None


# -----------------------------------------------------------------------------
# RealtimeEvent — 23-kind discriminated union, keyed on ``kind``.
# -----------------------------------------------------------------------------


class _BaseEvent(BaseModel):
    """Base for all realtime events. Adds a frozen ``kind`` field per subclass."""

    model_config = ConfigDict(arbitrary_types_allowed=True)


class SessionOpenedEvent(_BaseEvent):
    kind: Literal["session_opened"] = "session_opened"
    session_id: str


class SessionUpdatedEvent(_BaseEvent):
    kind: Literal["session_updated"] = "session_updated"
    config: Dict[str, Any]


class SessionClosedEvent(_BaseEvent):
    kind: Literal["session_closed"] = "session_closed"
    reason: Literal["client", "server", "error"]


class UserSpeechStartedEvent(_BaseEvent):
    kind: Literal["user_speech_started"] = "user_speech_started"
    at_ms: int


class UserSpeechStoppedEvent(_BaseEvent):
    kind: Literal["user_speech_stopped"] = "user_speech_stopped"
    at_ms: int


class UserTranscriptDeltaEvent(_BaseEvent):
    kind: Literal["user_transcript_delta"] = "user_transcript_delta"
    item_id: str
    delta: str


class UserTranscriptEvent(_BaseEvent):
    kind: Literal["user_transcript"] = "user_transcript"
    item_id: str
    text: str


class AssistantTurnStartedEvent(_BaseEvent):
    kind: Literal["assistant_turn_started"] = "assistant_turn_started"
    turn_id: str


class AssistantTextDeltaEvent(_BaseEvent):
    kind: Literal["assistant_text_delta"] = "assistant_text_delta"
    turn_id: str
    delta: str


class AssistantTextEvent(_BaseEvent):
    kind: Literal["assistant_text"] = "assistant_text"
    turn_id: str
    text: str


class AssistantTranscriptDeltaEvent(_BaseEvent):
    kind: Literal["assistant_transcript_delta"] = "assistant_transcript_delta"
    turn_id: str
    delta: str


class AssistantTranscriptEvent(_BaseEvent):
    kind: Literal["assistant_transcript"] = "assistant_transcript"
    turn_id: str
    text: str


class AssistantAudioDeltaEvent(_BaseEvent):
    """
    A chunk of decoded PCM16 audio for the current assistant turn.

    ``pcm`` is a ``numpy.ndarray`` with ``dtype=int16``. Decoding happens
    at the gateway boundary so consumer code never touches base64.
    """

    kind: Literal["assistant_audio_delta"] = "assistant_audio_delta"
    turn_id: str
    pcm: np.ndarray = Field(...)


class AssistantTurnCompletedEvent(_BaseEvent):
    kind: Literal["assistant_turn_completed"] = "assistant_turn_completed"
    turn_id: str
    usage: Optional[TokenUsage] = None


class ToolCallStartedEvent(_BaseEvent):
    kind: Literal["tool_call_started"] = "tool_call_started"
    turn_id: str
    call_id: str
    name: str


class ToolCallArgsDeltaEvent(_BaseEvent):
    kind: Literal["tool_call_args_delta"] = "tool_call_args_delta"
    call_id: str
    delta: str


class ToolCallDispatchedEvent(_BaseEvent):
    kind: Literal["tool_call_dispatched"] = "tool_call_dispatched"
    call_id: str
    name: str
    args: Dict[str, Any]


class ToolCallCompletedEvent(_BaseEvent):
    kind: Literal["tool_call_completed"] = "tool_call_completed"
    call_id: str
    name: str
    result: Any


class ToolCallFailedEvent(_BaseEvent):
    kind: Literal["tool_call_failed"] = "tool_call_failed"
    call_id: str
    name: str
    error: BaseException

    model_config = ConfigDict(arbitrary_types_allowed=True)


class ToolBatchSubmittedEvent(_BaseEvent):
    kind: Literal["tool_batch_submitted"] = "tool_batch_submitted"
    turn_id: str
    call_ids: List[str]


class InterruptedEvent(_BaseEvent):
    kind: Literal["interrupted"] = "interrupted"
    turn_id: str
    reason: Literal["barge_in", "manual", "error"]


class RateLimitedEvent(_BaseEvent):
    kind: Literal["rate_limited"] = "rate_limited"
    reset_ms: int
    details: Dict[str, Any]


class ErrorEvent(_BaseEvent):
    kind: Literal["error"] = "error"
    error: BaseException
    recoverable: bool

    model_config = ConfigDict(arbitrary_types_allowed=True)


RealtimeEvent = Union[
    SessionOpenedEvent,
    SessionUpdatedEvent,
    SessionClosedEvent,
    UserSpeechStartedEvent,
    UserSpeechStoppedEvent,
    UserTranscriptDeltaEvent,
    UserTranscriptEvent,
    AssistantTurnStartedEvent,
    AssistantTextDeltaEvent,
    AssistantTextEvent,
    AssistantTranscriptDeltaEvent,
    AssistantTranscriptEvent,
    AssistantAudioDeltaEvent,
    AssistantTurnCompletedEvent,
    ToolCallStartedEvent,
    ToolCallArgsDeltaEvent,
    ToolCallDispatchedEvent,
    ToolCallCompletedEvent,
    ToolCallFailedEvent,
    ToolBatchSubmittedEvent,
    InterruptedEvent,
    RateLimitedEvent,
    ErrorEvent,
]
"""
Vendor-neutral event types emitted by :class:`RealtimeSession`.

The ``kind`` field discriminates the variant. Pattern match on ``kind``
in ``match`` statements or ``if`` chains to handle each type.
"""
