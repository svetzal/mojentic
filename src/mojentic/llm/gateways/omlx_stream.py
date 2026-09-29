"""
Pure functions over oMLX chat completions server-sent-event lines.

oMLX opens every chat stream with a keep-alive frame, a real ``data:`` frame whose
``model`` is ``keepalive``, and sends more during long prefill.
:func:`drop_keepalive_frames` removes them before any parser sees them, so a stream that
fails during prefill never reports ``keepalive`` as the provider model.
:func:`omlx_stream_chunks` turns the remaining lines into the legacy streaming chunks.
"""
import json
from typing import Dict, Iterable, Iterator, List, Optional

import structlog

from mojentic.llm.gateways.models import LLMToolCall
from mojentic.llm.gateways.ollama import StreamingResponse
from mojentic.llm.gateways.openai_stream_events import DONE_MARKER, sse_data

logger = structlog.get_logger()

KEEPALIVE_MODEL = "keepalive"


def drop_keepalive_frames(lines: Iterable[str]) -> Iterator[str]:
    """
    Yield every line except keep-alive frames.

    Parameters
    ----------
    lines : Iterable[str]
        Raw SSE lines.

    Yields
    ------
    str
        The lines, minus ``data:`` frames whose ``model`` is ``keepalive``. Comments and
        frames that do not decode pass through unchanged, for the parser to judge.
    """
    return (line for line in lines if not _is_keepalive(line))


def _is_keepalive(line: str) -> bool:
    frame = _decoded_frame(line)
    return isinstance(frame, dict) and frame.get("model") == KEEPALIVE_MODEL


def _decoded_frame(line: str) -> Optional[object]:
    data = sse_data(line)
    if data is None or data == DONE_MARKER:
        return None
    try:
        return json.loads(data)
    except json.JSONDecodeError:
        return None


def omlx_stream_chunks(lines: Iterable[str]) -> Iterator[StreamingResponse]:
    """
    Yield legacy streaming chunks for one oMLX chat completions stream.

    ``delta.content`` becomes a content chunk and ``delta.reasoning_content`` a thinking
    chunk. Tool call deltas are accumulated by index and yielded together, as
    :class:`LLMToolCall` objects, when the finish reason is ``tool_calls``. oMLX sends each
    tool call complete in one delta; fragmented arguments are accumulated as well.

    Parameters
    ----------
    lines : Iterable[str]
        Raw SSE lines, with keep-alive frames already removed.

    Yields
    ------
    StreamingResponse
        Content, thinking and tool call chunks. Reading stops at ``data: [DONE]``.
    """
    tool_calls: Dict[int, dict] = {}
    for line in lines:
        data = sse_data(line)
        if data == DONE_MARKER:
            return
        if data is None:
            continue
        choices = json.loads(data).get("choices") or []
        for choice in choices:
            yield from _choice_chunks(choice, tool_calls)


def _choice_chunks(choice: dict, tool_calls: Dict[int, dict]) -> Iterator[StreamingResponse]:
    delta = choice.get("delta") or {}
    if delta.get("content"):
        yield StreamingResponse(content=delta["content"])
    if delta.get("reasoning_content"):
        yield StreamingResponse(thinking=delta["reasoning_content"])
    for fragment in delta.get("tool_calls") or []:
        _accumulate(tool_calls, fragment)
    if choice.get("finish_reason") == "tool_calls" and tool_calls:
        complete = _complete_tool_calls(tool_calls)
        if complete:
            yield StreamingResponse(tool_calls=complete)


def _accumulate(tool_calls: Dict[int, dict], fragment: dict) -> None:
    call = tool_calls.setdefault(fragment.get("index", 0), {"id": None, "name": None, "arguments": ""})
    function = fragment.get("function") or {}
    call["id"] = fragment.get("id") or call["id"]
    call["name"] = function.get("name") or call["name"]
    call["arguments"] += function.get("arguments") or ""


def _complete_tool_calls(tool_calls: Dict[int, dict]) -> List[LLMToolCall]:
    complete = []
    for index in sorted(tool_calls):
        call = tool_calls[index]
        try:
            complete.append(LLMToolCall(id=call["id"], name=call["name"], arguments=json.loads(call["arguments"])))
        except json.JSONDecodeError as e:
            logger.error("Failed to parse tool call arguments", tool_name=call["name"],
                         arguments=call["arguments"], error=str(e))
    return complete
