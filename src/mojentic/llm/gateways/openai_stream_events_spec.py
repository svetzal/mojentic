import json

from mojentic.llm.gateways.openai_stream_events import parse_openai_stream
from mojentic.llm.gateways.stream_events import (
    CompletionMetadata,
    StreamCompleted,
    StreamContent,
    StreamError,
    StreamErrorReason,
)

USAGE = {"prompt_tokens": 8, "completion_tokens": 2, "total_tokens": 10}


def _data(frame: dict) -> str:
    return f"data: {json.dumps(frame)}"


def _delta(delta: dict, finish_reason=None) -> str:
    return _data({"model": "gpt-4o-2024-08-06",
                  "choices": [{"index": 0, "delta": delta, "finish_reason": finish_reason}]})


def _usage() -> str:
    return _data({"model": "gpt-4o-2024-08-06", "choices": [], "usage": USAGE})


class DescribeParseOpenAIStream:

    def should_yield_content_then_completed_after_stop_and_done(self):
        lines = [_delta({"role": "assistant", "content": "Hel"}), "", _delta({"content": "lo"}),
                 _delta({}, finish_reason="stop"), _usage(), "data: [DONE]"]

        events = list(parse_openai_stream(lines))

        assert events == [
            StreamContent(text="Hel"),
            StreamContent(text="lo"),
            StreamCompleted(metadata=CompletionMetadata(
                finish_reason="stop", usage=USAGE, provider_model="gpt-4o-2024-08-06")),
        ]

    def should_report_incomplete_completion_when_done_follows_length(self):
        lines = [_delta({"content": "Hel"}), _delta({}, finish_reason="length"), _usage(), "data: [DONE]"]

        events = list(parse_openai_stream(lines))

        assert events[-1] == StreamError(
            reason=StreamErrorReason.INCOMPLETE_COMPLETION,
            metadata=CompletionMetadata(finish_reason="length", usage=USAGE, provider_model="gpt-4o-2024-08-06"))

    def should_report_incomplete_completion_when_done_arrives_without_finish_reason(self):
        events = list(parse_openai_stream([_delta({"content": "Hel"}), "data: [DONE]"]))

        assert events[-1].reason == StreamErrorReason.INCOMPLETE_COMPLETION

    def should_report_incomplete_stream_when_lines_end_without_done(self):
        lines = [_delta({"content": "Hel"}), _delta({}, finish_reason="stop")]

        events = list(parse_openai_stream(lines))

        assert events[-1] == StreamError(
            reason=StreamErrorReason.INCOMPLETE_STREAM,
            metadata=CompletionMetadata(finish_reason="stop", provider_model="gpt-4o-2024-08-06"))

    def should_reject_tool_call_deltas(self):
        tool_delta = {"tool_calls": [{"index": 0, "id": "call_1", "function": {"name": "f", "arguments": ""}}]}

        events = list(parse_openai_stream([_delta(tool_delta), "data: [DONE]"]))

        assert events == [StreamError(reason=StreamErrorReason.UNEXPECTED_TOOL_CALLS)]

    def should_reject_legacy_function_call_deltas(self):
        events = list(parse_openai_stream([_delta({"function_call": {"name": "f"}})]))

        assert events == [StreamError(reason=StreamErrorReason.UNEXPECTED_TOOL_CALLS)]

    def should_report_provider_error_frames(self):
        error = {"message": "overloaded", "type": "server_error"}

        events = list(parse_openai_stream([_delta({"content": "Hel"}), _data({"error": error})]))

        assert events[-1] == StreamError(reason=StreamErrorReason.PROVIDER_ERROR, detail=error)

    def should_report_malformed_frames_as_invalid(self):
        events = list(parse_openai_stream(["data: {not json"]))

        assert events == [StreamError(reason=StreamErrorReason.INVALID_STREAM_EVENT, detail="{not json")]

    def should_report_frames_without_choices_as_invalid(self):
        events = list(parse_openai_stream([_data({"object": "surprise"})]))

        assert events[-1].reason == StreamErrorReason.INVALID_STREAM_EVENT

    def should_report_non_text_content_as_invalid(self):
        events = list(parse_openai_stream([_delta({"content": ["part"]})]))

        assert events[-1].reason == StreamErrorReason.INVALID_STREAM_EVENT

    def should_ignore_comments_and_other_sse_fields(self):
        lines = [": keep-alive", "event: message", _delta({"content": "Hi"}, finish_reason="stop"), "data: [DONE]"]

        events = list(parse_openai_stream(lines))

        assert [type(event) for event in events] == [StreamContent, StreamCompleted]

    def should_accept_data_fields_without_a_space(self):
        lines = ['data:{"choices":[{"delta":{"content":"Hi"},"finish_reason":"stop"}]}', "data:[DONE]"]

        events = list(parse_openai_stream(lines))

        assert [type(event) for event in events] == [StreamContent, StreamCompleted]

    def should_stop_reading_after_the_terminal_event(self):
        read = []

        def lines():
            for line in [_delta({"content": "Hi"}, finish_reason="stop"), "data: [DONE]", _delta({"content": "x"})]:
                read.append(line)
                yield line

        list(parse_openai_stream(lines()))

        assert len(read) == 2
