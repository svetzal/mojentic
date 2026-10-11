"""oMLX decoding over the shared owned HTTP recovery lifecycle.

Legacy parsers retain their single-request behavior. This decoder requires a safe
finish and [DONE], and observes semantics before invoking caller capture hooks.
"""

import json
from collections.abc import Callable

import httpx
from pydantic import BaseModel

from mojentic.llm.gateways.models import LLMGatewayResponse
from mojentic.llm.gateways.omlx_protocol import (
    omlx_gateway_response,
    requests_structured_output,
)
from mojentic.llm.recovery import _Attempt, _Recovery
from mojentic.llm.recovery_stream import (
    RecoveryStreamEvent,
    StreamFrameProgress,
    StreamMetrics,
    _Decoder,
    _StreamRecovery,
)


class OMLXRecovery(_Recovery):
    """Retain structured-output warnings without logging untrusted header values."""

    provider = "omlx"

    async def exchange(
        self,
        client: httpx.AsyncClient,
        url: str,
        body: bytes,
        headers: dict,
        attempt: _Attempt,
        decode: Callable[[object], LLMGatewayResponse],
    ) -> LLMGatewayResponse:
        result = await super().exchange(client, url, body, headers, attempt, decode)
        if requests_structured_output(json.loads(body)):
            warnings = httpx.Headers(attempt.headers).get_list("warning")
            if warnings:
                result.metadata["response_format_warning"] = ", ".join(warnings)
        return result


def _completion_message(frame: object) -> dict:
    if not isinstance(frame, dict):
        raise TypeError("invalid completion")
    choices = frame.get("choices")
    if (
        not isinstance(choices, list)
        or len(choices) != 1
        or not isinstance(choices[0], dict)
    ):
        raise ValueError("expected one choice")
    message = choices[0].get("message")
    if not isinstance(message, dict):
        raise TypeError("missing completion message")
    for field in ("content", "reasoning_content"):
        if message.get(field) is not None and not isinstance(message[field], str):
            raise TypeError("invalid completion text")
    return message


def _validate_tools(message: dict) -> None:
    calls = [] if message.get("tool_calls") is None else message["tool_calls"]
    if not isinstance(calls, list):
        raise TypeError("invalid completion tools")
    for call in calls:
        if not isinstance(call, dict) or not isinstance(call.get("function"), dict):
            raise TypeError("invalid completion tool")
        function = call["function"]
        if not isinstance(function.get("name"), str) or not function["name"]:
            raise ValueError("missing tool name")
        if not isinstance(function.get("arguments"), str) or not isinstance(
            json.loads(function["arguments"]), dict
        ):
            raise TypeError("invalid tool arguments")


def decode_completion(
    frame: object,
    object_model: type[BaseModel] | None = None,
) -> LLMGatewayResponse:
    """Validate response shape and schema without changing ordinary finish handling."""
    message = _completion_message(frame)
    _validate_tools(message)
    result = omlx_gateway_response(frame)
    if result.content is None and result.thinking is None and not result.tool_calls:
        raise ValueError("empty completion")
    if object_model is not None:
        result.object = object_model.model_validate_json(result.content)
    return result


class _OMLXDecoder(_Decoder):
    def __init__(self) -> None:
        super().__init__()
        self.fragments = {}
        self.finish = None

    def observe(self, frame: object, attempt: _Attempt) -> None:
        if not isinstance(frame, dict) or frame.get("model") == "keepalive":
            return
        choices = frame.get("choices")
        if not isinstance(choices, list):
            return
        for choice in choices:
            delta = choice.get("delta") if isinstance(choice, dict) else None
            if not isinstance(delta, dict):
                continue
            calls = delta.get("tool_calls")
            attempt.progress = attempt.progress.model_copy(
                update={
                    "observed_content": attempt.progress.observed_content
                    or bool(delta.get("content")),
                    "observed_reasoning": attempt.progress.observed_reasoning
                    or bool(delta.get("reasoning_content")),
                    "observed_tool_fragments": attempt.progress.observed_tool_fragments
                    + (len(calls) if isinstance(calls, list) else 0),
                }
            )

    def events(
        self, frame: object, attempt: _Attempt
    ) -> tuple[list[RecoveryStreamEvent], bool]:
        if frame == "[DONE]":
            if self.finish not in {"stop", "tool_calls"}:
                raise ValueError("terminal marker without safe finish")
            self.tools = self.completed_tools()
            self.terminal = True
            return [], True
        if not isinstance(frame, dict):
            raise TypeError("invalid stream frame")
        if frame.get("model") == "keepalive":
            return [], True
        if frame.get("error") is not None:
            raise ValueError("provider stream error")
        self.index += 1
        common = {
            "identity": attempt.identity,
            "progress": attempt.progress,
            "frame_index": self.index,
        }
        output = []
        self.metadata(frame, common, output)
        choices = frame.get("choices")
        if not isinstance(choices, list):
            raise TypeError("missing stream choices")
        if choices == [] and frame.get("usage") is not None:
            return output, True
        if len(choices) != 1 or not isinstance(choices[0], dict):
            raise ValueError("expected one stream choice")
        events, accepted = self.choice_events(choices[0], common)
        return output + events, accepted

    def choice_events(
        self, choice: dict, common: dict
    ) -> tuple[list[RecoveryStreamEvent], bool]:
        output = []
        delta = choice.get("delta")
        if not isinstance(delta, dict):
            raise TypeError("missing stream delta")
        finish = choice.get("finish_reason")
        if finish is not None:
            if not isinstance(finish, str):
                raise TypeError("invalid finish")
            self.finish = finish
            self.evidence["finish_reason"] = finish
        content = self.text(delta, "content")
        thinking = self.text(delta, "reasoning_content")
        calls = [] if delta.get("tool_calls") is None else delta["tool_calls"]
        if not isinstance(calls, list):
            raise TypeError("invalid tool fragments")
        output.append(
            RecoveryStreamEvent(
                kind="progress",
                frame_progress=StreamFrameProgress(
                    provider="omlx",
                    done=False,
                    content_bytes=len(content.encode()),
                    reasoning_bytes=len(thinking.encode()),
                    tool_call_count=len(calls),
                    accumulated_tool_call_count=len(self.fragments),
                ),
                **common,
            )
        )
        if finish is not None:
            output.append(self.metrics(common))
        if finish is not None and finish not in {"stop", "tool_calls"}:
            return output, False
        return output + self.semantic_events(content, thinking, calls, common), True

    def semantic_events(
        self,
        content: str,
        thinking: str,
        calls: list,
        common: dict,
    ) -> list[RecoveryStreamEvent]:
        output = []
        self.content += content
        self.thinking += thinking
        if content:
            output.append(RecoveryStreamEvent(kind="content", text=content, **common))
        if thinking:
            output.append(
                RecoveryStreamEvent(kind="reasoning", text=thinking, **common)
            )
        for call in calls:
            self.accumulate(call)
            output.append(
                RecoveryStreamEvent(kind="tool_fragment", tools=(call,), **common)
            )
        return output

    @staticmethod
    def text(delta: dict, key: str) -> str:
        value = delta.get(key)
        if value is not None and not isinstance(value, str):
            raise TypeError("invalid delta text")
        return value or ""

    def metadata(
        self, frame: dict, common: dict, output: list[RecoveryStreamEvent]
    ) -> None:
        if frame.get("model") is not None:
            if not isinstance(frame["model"], str):
                raise TypeError("invalid model")
            self.evidence["model"] = frame["model"]
        usage = frame.get("usage")
        if usage is not None:
            if not isinstance(usage, dict) or any(
                key in usage and (type(usage[key]) is not int or usage[key] < 0)
                for key in ("prompt_tokens", "completion_tokens", "total_tokens")
            ):
                raise TypeError("invalid usage")
            self.evidence["usage"] = usage
            output.append(self.metrics(common))

    def metrics(self, common: dict) -> RecoveryStreamEvent:
        return RecoveryStreamEvent(
            kind="metrics",
            metrics=StreamMetrics(
                provider="omlx",
                provider_model=self.evidence.get("model"),
                finish_reason=self.finish,
                usage=self.evidence.get("usage"),
            ),
            **common,
        )

    def accumulate(self, fragment: object) -> None:
        if (
            not isinstance(fragment, dict)
            or type(fragment.get("index")) is not int
            or fragment["index"] < 0
        ):
            raise TypeError("invalid tool index")
        call = self.fragments.setdefault(
            fragment["index"], {"id": None, "name": "", "arguments": ""}
        )
        function = {} if fragment.get("function") is None else fragment["function"]
        if not isinstance(function, dict):
            raise TypeError("invalid tool function")
        if fragment.get("id") is not None:
            call["id"] = self.text(fragment, "id")
        call["name"] += self.text(function, "name")
        call["arguments"] += self.text(function, "arguments")

    def completed_tools(self) -> list[dict]:
        tools = []
        for index in sorted(self.fragments):
            call = self.fragments[index]
            arguments = json.loads(call["arguments"])
            if not call["name"] or not isinstance(arguments, dict):
                raise ValueError("invalid completed tool")
            tools.append(
                {
                    "id": call["id"],
                    "function": {"name": call["name"], "arguments": arguments},
                }
            )
        return tools


class OMLXStreamRecovery(_StreamRecovery):
    """SSE framing over the shared cancellation, admission and attempt engine."""

    provider = "omlx"

    def decoder(self) -> _OMLXDecoder:
        return _OMLXDecoder()

    @staticmethod
    def data(line: bytes) -> bytes | None:
        if line.startswith(b"data:"):
            return line[5:].strip()
        if not line.strip() or line.startswith((b":", b"event:", b"id:", b"retry:")):
            return None
        raise ValueError("invalid SSE line")

    def observe_chunk(
        self,
        lines: list[bytes],
        pending: bytes,
        decoder: _OMLXDecoder,
        attempt: _Attempt,
    ) -> tuple[list[object], Exception | None]:
        frames, error = [], None
        for index, line in enumerate(lines):
            observed = index == 0 and decoder.pending_observed
            if index == 0:
                decoder.pending_observed = False
            try:
                data = self.data(line)
                if data is None:
                    continue
                frame = "[DONE]" if data == b"[DONE]" else json.loads(data)
                if not observed:
                    decoder.observe(frame, attempt)
                frames.append(frame)
            except (ValueError, UnicodeDecodeError) as cause:
                error = cause
        if pending and not decoder.pending_observed:
            try:
                data = self.data(pending)
                frame = json.loads(data) if data else None
            except (ValueError, UnicodeDecodeError):
                pass
            else:
                decoder.observe(frame, attempt)
                decoder.pending_observed = True
        return frames, error

    @staticmethod
    def response_frame(decoder: _OMLXDecoder) -> dict:
        return decoder.evidence | {
            "choices": [
                {
                    "finish_reason": decoder.finish,
                    "message": {
                        "content": decoder.content,
                        "reasoning_content": decoder.thinking,
                        "tool_calls": [
                            {
                                "id": t["id"],
                                "function": {
                                    "name": t["function"]["name"],
                                    "arguments": json.dumps(t["function"]["arguments"]),
                                },
                            }
                            for t in decoder.tools
                        ],
                    },
                }
            ]
        }
