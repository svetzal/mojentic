from mojentic.llm.gateways.ollama_stream_events import parse_ollama_stream
from mojentic.llm.gateways.stream_events import (
    CompletionMetadata,
    StreamCompleted,
    StreamContent,
    StreamError,
    StreamErrorReason,
)


def _content(text: str) -> dict:
    return {"model": "qwen3:32b", "done": False, "message": {"role": "assistant", "content": text}}


def _final(done_reason: str, **fields) -> dict:
    return {"model": "qwen3:32b", "done": True, "done_reason": done_reason,
            "message": {"role": "assistant", "content": ""}, "prompt_eval_count": 11, "eval_count": 4,
            "total_duration": 900, "eval_duration": 500} | fields


USAGE = {"prompt_eval_count": 11, "eval_count": 4}
DURATIONS = {"total_duration": 900, "eval_duration": 500}


class DescribeParseOllamaStream:

    def should_yield_content_then_completed_on_done_with_stop(self):
        events = list(parse_ollama_stream([_content("Hel"), _content("lo"), _final("stop")]))

        assert events == [
            StreamContent(text="Hel"),
            StreamContent(text="lo"),
            StreamCompleted(metadata=CompletionMetadata(finish_reason="stop", usage=USAGE,
                                                        provider_model="qwen3:32b", metadata=DURATIONS)),
        ]

    def should_yield_content_carried_on_the_final_frame_before_completing(self):
        final = _final("stop", message={"role": "assistant", "content": "!"})

        events = list(parse_ollama_stream([final]))

        assert [type(event) for event in events] == [StreamContent, StreamCompleted]

    def should_report_incomplete_completion_when_done_reason_is_length(self):
        events = list(parse_ollama_stream([_content("Hel"), _final("length")]))

        assert events[-1] == StreamError(
            reason=StreamErrorReason.INCOMPLETE_COMPLETION,
            metadata=CompletionMetadata(finish_reason="length", usage=USAGE, provider_model="qwen3:32b",
                                        metadata=DURATIONS))

    def should_leave_usage_unknown_when_counts_are_missing(self):
        final = _final("stop", prompt_eval_count=None, eval_count=None)

        events = list(parse_ollama_stream([final]))

        assert events[-1].metadata.usage is None

    def should_leave_provider_metadata_unknown_when_durations_are_missing(self):
        final = _final("stop", total_duration=None, eval_duration=None)

        events = list(parse_ollama_stream([final]))

        assert events[-1].metadata.metadata is None

    def should_report_incomplete_stream_when_frames_end_without_done(self):
        events = list(parse_ollama_stream([_content("Hel")]))

        assert events[-1] == StreamError(reason=StreamErrorReason.INCOMPLETE_STREAM,
                                         metadata=CompletionMetadata(provider_model="qwen3:32b"))

    def should_reject_tool_calls(self):
        frame = {"model": "qwen3:32b", "done": False,
                 "message": {"role": "assistant", "content": "",
                             "tool_calls": [{"function": {"name": "f", "arguments": {}}}]}}

        events = list(parse_ollama_stream([frame, _final("stop")]))

        assert events == [StreamError(reason=StreamErrorReason.UNEXPECTED_TOOL_CALLS)]

    def should_report_provider_error_frames(self):
        events = list(parse_ollama_stream([_content("Hel"), {"error": "model crashed"}]))

        assert events[-1] == StreamError(reason=StreamErrorReason.PROVIDER_ERROR, detail="model crashed")

    def should_report_non_text_content_as_invalid(self):
        frame = {"model": "qwen3:32b", "done": False, "message": {"role": "assistant", "content": 7}}

        events = list(parse_ollama_stream([frame]))

        assert events[-1].reason == StreamErrorReason.INVALID_STREAM_EVENT

    def should_report_non_object_frames_as_invalid(self):
        events = list(parse_ollama_stream(["surprise"]))

        assert events[-1].reason == StreamErrorReason.INVALID_STREAM_EVENT

    def should_stop_reading_after_the_terminal_event(self):
        read = []

        def frames():
            for frame in [_final("stop"), _content("late")]:
                read.append(frame)
                yield frame

        list(parse_ollama_stream(frames()))

        assert len(read) == 1
