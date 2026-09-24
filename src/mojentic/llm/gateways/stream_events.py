"""
Events yielded by single-turn streaming (``LLMBroker.generate_stream_events``).

Every stream yields zero or more :class:`StreamContent` events and ends with exactly one
terminal event: :class:`StreamCompleted` on success or :class:`StreamError` on failure.
Nothing follows the terminal event. Content yielded before a :class:`StreamError` is
evidence of what the provider sent, not a usable result.
"""
from enum import Enum
from typing import Annotated, Any, Dict, Literal, Optional, Union

from pydantic import BaseModel, ConfigDict, Field


class CompletionMetadata(BaseModel):
    """
    What the provider reported about how a turn ended.

    Every field is None when the provider did not report it. Nothing is estimated.

    Attributes
    ----------
    finish_reason : Optional[str]
        The provider's finish reason (OpenAI ``finish_reason``, Ollama ``done_reason``).
    usage : Optional[Dict[str, Any]]
        Token usage exactly as the provider reported it.
    provider_model : Optional[str]
        The model name the provider reported.
    metadata : Optional[Dict[str, Any]]
        Other provider-reported fields, such as Ollama's durations.
    """
    model_config = ConfigDict(frozen=True)

    finish_reason: Optional[str] = None
    usage: Optional[Dict[str, Any]] = None
    provider_model: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class StreamErrorReason(str, Enum):
    """Why a single-turn stream failed."""

    INCOMPLETE_COMPLETION = "incomplete_completion"
    """The provider finished the turn for a reason other than ``stop`` (for example ``length``)."""
    INCOMPLETE_STREAM = "incomplete_stream"
    """The stream ended without the provider's terminal marker."""
    PROVIDER_ERROR = "provider_error"
    """The provider sent an error frame or an error response."""
    UNEXPECTED_TOOL_CALLS = "unexpected_tool_calls"
    """The provider asked for a tool call; this API supplies no tools and runs none."""
    INVALID_STREAM_EVENT = "invalid_stream_event"
    """A frame could not be decoded or did not have the expected shape."""
    REQUEST_FAILED = "request_failed"
    """The request could not be sent or the connection failed mid-stream."""
    STREAM_EVENTS_UNSUPPORTED = "stream_events_unsupported"
    """The gateway or model does not support this API. No request was sent."""


class StreamContent(BaseModel):
    """Visible assistant content, in the order the provider sent it."""
    model_config = ConfigDict(frozen=True)

    type: Literal["content"] = "content"
    text: str


class StreamCompleted(BaseModel):
    """Terminal success: the provider finished the turn with ``stop`` and closed the stream properly."""
    model_config = ConfigDict(frozen=True)

    type: Literal["completed"] = "completed"
    metadata: CompletionMetadata


class StreamError(BaseModel):
    """
    Terminal failure.

    Attributes
    ----------
    reason : StreamErrorReason
        Why the stream failed.
    detail : Optional[Union[str, Dict[str, Any]]]
        Provider error payload, undecodable frame text, or failure message, when there is one.
    metadata : Optional[CompletionMetadata]
        Completion evidence the provider reported before the failure, when there is any.
    """
    model_config = ConfigDict(frozen=True)

    type: Literal["error"] = "error"
    reason: StreamErrorReason
    detail: Optional[Union[str, Dict[str, Any]]] = None
    metadata: Optional[CompletionMetadata] = None


StreamEvent = Annotated[Union[StreamContent, StreamCompleted, StreamError], Field(discriminator="type")]
"""One event from ``LLMBroker.generate_stream_events``."""

TerminalStreamEvent = Union[StreamCompleted, StreamError]
