from pathlib import Path

from mojentic.llm.gateways.models import LLMToolCall
from mojentic.llm.gateways.ollama import StreamingResponse
from mojentic.llm.gateways.omlx_stream import drop_keepalive_frames, omlx_stream_chunks

FIXTURES = Path(__file__).parent / "fixtures" / "omlx"

KEEPALIVE = (
    'data: {"id":"chatcmpl-1","object":"chat.completion.chunk","created":0,"model":"keepalive",'
    '"choices":[{"index":0,"delta":{"role":"assistant","content":""},"finish_reason":null}]}'
)


def fixture_lines(name):
    return (FIXTURES / name).read_text().splitlines()


class DescribeDropKeepaliveFrames:
    def should_drop_frames_whose_model_is_keepalive(self):
        lines = list(drop_keepalive_frames([KEEPALIVE, "", "data: [DONE]"]))

        assert lines == ["", "data: [DONE]"]

    def should_remove_the_keepalive_frame_from_every_fixture_stream(self):
        streams = ["stream_thinking.sse", "stream_length.sse", "stream_tool_call.sse"]

        survivors = [
            line
            for name in streams
            for line in drop_keepalive_frames(fixture_lines(name))
        ]

        assert '"model":"keepalive"' not in "".join(survivors)

    def should_keep_frames_from_the_real_model(self):
        frame = 'data: {"model":"Qwen3.8-27B-MLX-8bit","choices":[{"delta":{"content":"hi"}}]}'

        assert list(drop_keepalive_frames([frame])) == [frame]

    def should_pass_comments_and_undecodable_frames_through_to_the_parser(self):
        lines = [": keep-alive", "data: {not json", "data: [1, 2]"]

        assert list(drop_keepalive_frames(lines)) == lines


class DescribeOMLXStreamChunks:
    def should_yield_reasoning_content_as_thinking_and_content_as_content(self):
        chunks = list(omlx_stream_chunks(fixture_lines("stream_thinking.sse")))

        assert (
            "".join(c.thinking for c in chunks if c.thinking),
            [c.content for c in chunks if c.content],
        ) == (
            (
                '\nWe need to reply exactly: hello. User said "Reply with exactly: hello". Need final "hello". '
                "Ensure no extra.\n"
            ),
            ["\n\nhello"],
        )

    def should_yield_one_complete_tool_call_from_the_fixture(self):
        chunks = list(omlx_stream_chunks(fixture_lines("stream_tool_call.sse")))

        assert [c.tool_calls for c in chunks if c.tool_calls] == [
            [
                LLMToolCall(
                    id="call_659d0e77",
                    name="resolve_date",
                    arguments={"relative": "today"},
                )
            ]
        ]

    def should_accumulate_tool_call_arguments_sent_in_fragments(self):
        lines = [
            (
                'data: {"choices":[{"delta":{"tool_calls":[{"index":0,"id":"call_1",'
                '"function":{"name":"resolve_date","arguments":"{\\"rel"}}]}}]}'
            ),
            'data: {"choices":[{"delta":{"tool_calls":[{"index":0,"function":{"arguments":"ative\\": \\"today\\"}"}}]}}]}',
            'data: {"choices":[{"delta":{},"finish_reason":"tool_calls"}]}',
            "data: [DONE]",
        ]

        chunks = list(omlx_stream_chunks(lines))

        assert chunks == [
            StreamingResponse(
                tool_calls=[
                    LLMToolCall(
                        id="call_1",
                        name="resolve_date",
                        arguments={"relative": "today"},
                    )
                ]
            )
        ]

    def should_skip_a_tool_call_whose_arguments_are_not_json(self):
        lines = [
            'data: {"choices":[{"delta":{"tool_calls":[{"index":0,"id":"c","function":{"name":"t","arguments":"{"}}]}}]}',
            'data: {"choices":[{"delta":{},"finish_reason":"tool_calls"}]}',
        ]

        assert list(omlx_stream_chunks(lines)) == []

    def should_ignore_usage_frames_without_choices(self):
        lines = ['data: {"choices":[],"usage":{"prompt_tokens":1}}', "data: [DONE]"]

        assert list(omlx_stream_chunks(lines)) == []

    def should_stop_reading_at_the_done_marker(self):
        lines = ["data: [DONE]", 'data: {"choices":[{"delta":{"content":"late"}}]}']

        assert list(omlx_stream_chunks(lines)) == []
