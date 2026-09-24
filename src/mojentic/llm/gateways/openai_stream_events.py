"""
Turn an OpenAI-compatible chat completions server-sent-event stream into stream events.

Pure functions over the raw SSE lines, so the completion rules are testable without a
network. A turn succeeds only when the provider reports ``finish_reason: "stop"`` and
then sends ``data: [DONE]``.
"""
import json
from typing import Iterable, Iterator, List, Optional, Tuple

from mojentic.llm.gateways.stream_events import (
    CompletionMetadata,
    StreamCompleted,
    StreamContent,
    StreamError,
    StreamErrorReason,
    StreamEvent,
)

DONE_MARKER = "[DONE]"

FrameResult = Tuple[List[StreamEvent], CompletionMetadata]


def parse_openai_stream(lines: Iterable[str]) -> Iterator[StreamEvent]:
    """
    Yield stream events for one OpenAI-compatible streaming response.

    Parameters
    ----------
    lines : Iterable[str]
        The raw SSE lines of the response body, without line terminators.

    Yields
    ------
    StreamEvent
        Content events followed by exactly one terminal event. Reading stops at the
        terminal event.
    """
    evidence = CompletionMetadata()
    for line in lines:
        data = _sse_data(line)
        if data is None:
            continue
        if data == DONE_MARKER:
            yield _done(evidence)
            return
        events, evidence = _parse_frame(data, evidence)
        yield from events
        if events and not isinstance(events[-1], StreamContent):
            return
    yield StreamError(reason=StreamErrorReason.INCOMPLETE_STREAM, metadata=evidence)


def _sse_data(line: str) -> Optional[str]:
    """Return the value of an SSE ``data`` field, or None for comments, blanks and other fields."""
    if not line.startswith("data:"):
        return None
    data = line[len("data:"):]
    return data[1:] if data.startswith(" ") else data


def _done(evidence: CompletionMetadata) -> StreamEvent:
    if evidence.finish_reason == "stop":
        return StreamCompleted(metadata=evidence)
    return StreamError(reason=StreamErrorReason.INCOMPLETE_COMPLETION, metadata=evidence)


def _parse_frame(data: str, evidence: CompletionMetadata) -> FrameResult:
    try:
        frame = json.loads(data)
    except json.JSONDecodeError:
        return [StreamError(reason=StreamErrorReason.INVALID_STREAM_EVENT, detail=data)], evidence
    if not isinstance(frame, dict):
        return [_invalid(data)], evidence
    if "error" in frame:
        return [StreamError(reason=StreamErrorReason.PROVIDER_ERROR, detail=frame["error"])], evidence
    choices = frame.get("choices")
    if not isinstance(choices, list) or len(choices) > 1:
        return [_invalid(data)], evidence
    evidence = _fold_evidence(evidence, frame, choices)
    if not choices:
        return [], evidence
    return _delta_events(choices[0], data), evidence


def _fold_evidence(evidence: CompletionMetadata, frame: dict, choices: list) -> CompletionMetadata:
    reported = {
        "provider_model": frame.get("model"),
        "usage": frame.get("usage"),
        "finish_reason": choices[0].get("finish_reason") if choices and isinstance(choices[0], dict) else None,
    }
    updates = {field: value for field, value in reported.items() if value is not None}
    return evidence.model_copy(update=updates) if updates else evidence


def _delta_events(choice: object, data: str) -> List[StreamEvent]:
    delta = choice.get("delta") if isinstance(choice, dict) else None
    if not isinstance(delta, dict):
        return [_invalid(data)]
    if delta.get("tool_calls") or delta.get("function_call"):
        return [StreamError(reason=StreamErrorReason.UNEXPECTED_TOOL_CALLS)]
    content = delta.get("content")
    if content is None or content == "":
        return []
    if not isinstance(content, str):
        return [_invalid(data)]
    return [StreamContent(text=content)]


def _invalid(data: str) -> StreamError:
    return StreamError(reason=StreamErrorReason.INVALID_STREAM_EVENT, detail=data)
