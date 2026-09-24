"""
Turn an Ollama ``/api/chat`` streaming response into stream events.

Pure functions over the decoded response frames, so the completion rules are testable
without a network. A turn succeeds only when a frame reports ``done: true`` with a
``done_reason`` of ``stop``.
"""
from typing import Iterable, Iterator, List, Optional

from mojentic.llm.gateways.stream_events import (
    CompletionMetadata,
    StreamCompleted,
    StreamContent,
    StreamError,
    StreamErrorReason,
    StreamEvent,
)

OLLAMA_USAGE_FIELDS = ("prompt_eval_count", "eval_count")
OLLAMA_METADATA_FIELDS = ("total_duration", "load_duration", "prompt_eval_duration", "eval_duration")


def ollama_usage(frame: dict) -> Optional[dict]:
    """Token counts an Ollama response frame reported, under Ollama's own names, or None."""
    return _reported(frame, OLLAMA_USAGE_FIELDS)


def ollama_metadata(frame: dict) -> Optional[dict]:
    """Timing fields an Ollama response frame reported, or None."""
    return _reported(frame, OLLAMA_METADATA_FIELDS)


def parse_ollama_stream(frames: Iterable[object]) -> Iterator[StreamEvent]:
    """
    Yield stream events for one Ollama streaming chat response.

    Parameters
    ----------
    frames : Iterable[object]
        The decoded JSON frames of the response, in order.

    Yields
    ------
    StreamEvent
        Content events followed by exactly one terminal event. Reading stops at the
        terminal event.
    """
    provider_model = None
    for frame in frames:
        events = _frame_events(frame)
        yield from events
        if events and not isinstance(events[-1], StreamContent):
            return
        provider_model = frame.get("model") or provider_model
    yield StreamError(reason=StreamErrorReason.INCOMPLETE_STREAM,
                      metadata=CompletionMetadata(provider_model=provider_model) if provider_model else None)


def _frame_events(frame: object) -> List[StreamEvent]:
    if not isinstance(frame, dict):
        return [_invalid(frame)]
    if frame.get("error") is not None:
        return [StreamError(reason=StreamErrorReason.PROVIDER_ERROR, detail=frame["error"])]
    message = frame.get("message") or {}
    if not isinstance(message, dict):
        return [_invalid(frame)]
    if message.get("tool_calls"):
        return [StreamError(reason=StreamErrorReason.UNEXPECTED_TOOL_CALLS)]
    content = message.get("content")
    if content is not None and not isinstance(content, str):
        return [_invalid(frame)]
    events: List[StreamEvent] = [StreamContent(text=content)] if content else []
    if frame.get("done"):
        events.append(_terminal(frame))
    return events


def _terminal(frame: dict) -> StreamEvent:
    evidence = CompletionMetadata(
        finish_reason=frame.get("done_reason"),
        usage=ollama_usage(frame),
        provider_model=frame.get("model"),
        metadata=ollama_metadata(frame),
    )
    if evidence.finish_reason == "stop":
        return StreamCompleted(metadata=evidence)
    return StreamError(reason=StreamErrorReason.INCOMPLETE_COMPLETION, metadata=evidence)


def _reported(frame: dict, fields) -> Optional[dict]:
    reported = {field: frame[field] for field in fields if frame.get(field) is not None}
    return reported or None


def _invalid(frame: object) -> StreamError:
    return StreamError(reason=StreamErrorReason.INVALID_STREAM_EVENT, detail=str(frame))
