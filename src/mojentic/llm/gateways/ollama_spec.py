import json

import pytest
from ollama import ChatResponse, Message, ResponseError

from mojentic.llm.completion_config import CompletionConfig, ResponseFormat
from mojentic.llm.gateways.stream_events import StreamCompleted, StreamContent, StreamError, StreamErrorReason
from mojentic.llm.gateways.models import LLMMessage, MessageRole
from mojentic.llm.gateways.ollama import OllamaGateway


@pytest.fixture
def mock_ollama_client(mocker):
    return mocker.MagicMock()


@pytest.fixture
def gateway(mocker, mock_ollama_client):
    mocker.patch('mojentic.llm.gateways.ollama.Client', return_value=mock_ollama_client)
    return OllamaGateway()


@pytest.fixture
def messages():
    return [LLMMessage(role=MessageRole.User, content="Hello")]


def _final_frame(**overrides):
    fields = dict(model="qwen3:32b", done=True, done_reason="stop", prompt_eval_count=11, eval_count=5,
                  total_duration=900, load_duration=100, prompt_eval_duration=300, eval_duration=500,
                  message=Message(role="assistant", content="Hi"))
    return ChatResponse(**(fields | overrides))


class DescribeOllamaGateway:

    class DescribeResponseEvidence:

        def should_report_provider_evidence_on_completion(self, gateway, mock_ollama_client, messages):
            mock_ollama_client.chat.return_value = _final_frame()

            response = gateway.complete(model="qwen3:32b", messages=messages, config=CompletionConfig())

            assert (response.usage, response.model, response.finish_reason, response.metadata) == (
                {"prompt_eval_count": 11, "eval_count": 5}, "qwen3:32b", "stop",
                {"total_duration": 900, "load_duration": 100, "prompt_eval_duration": 300, "eval_duration": 500})

        def should_leave_usage_unknown_when_counts_are_not_reported(self, gateway, mock_ollama_client, messages):
            mock_ollama_client.chat.return_value = _final_frame(prompt_eval_count=None, eval_count=None)

            response = gateway.complete(model="qwen3:32b", messages=messages, config=CompletionConfig())

            assert response.usage is None


def _generator(items):
    yield from items


def _tracked(frames, closed):
    try:
        yield from frames
    finally:
        closed.append(True)


class DescribeStreamEvents:

    @pytest.fixture
    def transport(self, mocker):
        from mojentic.llm.gateways.ollama import OllamaStreamTransport
        return mocker.Mock(spec=OllamaStreamTransport)

    @pytest.fixture
    def gateway(self, mocker, transport):
        mocker.patch('mojentic.llm.gateways.ollama.Client')
        return OllamaGateway(stream_transport=transport)

    def should_send_one_streaming_request_without_tools(self, gateway, transport, messages):
        transport.stream_frames.return_value = _generator([])
        config = CompletionConfig(response_format=ResponseFormat(type="json_object"))

        list(gateway.complete_stream_events(model="qwen3:32b", messages=messages, config=config))

        request = transport.stream_frames.call_args.args[0]
        assert (transport.stream_frames.call_count, request["model"], request["format"], "tools" in request) == (
            1, "qwen3:32b", "json", False)

    def should_parse_the_provider_stream_into_events(self, gateway, transport, messages):
        transport.stream_frames.return_value = _generator([
            {"model": "qwen3:32b", "done": False, "message": {"role": "assistant", "content": "Hi"}},
            {"model": "qwen3:32b", "done": True, "done_reason": "stop", "message": {"role": "assistant"}},
        ])

        events = list(gateway.complete_stream_events(model="qwen3:32b", messages=messages, config=CompletionConfig()))

        assert [type(event) for event in events] == [StreamContent, StreamCompleted]

    def should_close_the_request_after_the_terminal_event(self, gateway, transport, messages):
        closed = []
        transport.stream_frames.return_value = _tracked(
            iter([{"model": "m", "done": True, "done_reason": "stop"}]), closed)

        list(gateway.complete_stream_events(model="qwen3:32b", messages=messages, config=CompletionConfig()))

        assert closed == [True]

    def should_report_provider_error_responses(self, gateway, transport, messages):
        def failing(request):
            raise ResponseError("model 'nope' not found", 404)
            yield

        transport.stream_frames.side_effect = failing

        events = list(gateway.complete_stream_events(model="nope", messages=messages, config=CompletionConfig()))

        assert events == [StreamError(reason=StreamErrorReason.PROVIDER_ERROR,
                                      detail={"status_code": 404, "error": "model 'nope' not found"})]

    def should_report_undecodable_frames_as_invalid(self, gateway, transport, messages):
        def failing(request):
            raise json.JSONDecodeError("Expecting value", "{oops", 1)
            yield

        transport.stream_frames.side_effect = failing

        events = list(gateway.complete_stream_events(model="qwen3:32b", messages=messages, config=CompletionConfig()))

        assert events[-1].reason == StreamErrorReason.INVALID_STREAM_EVENT

    def should_report_connection_failure_as_request_failed(self, gateway, transport, messages):
        def failing(request):
            raise ConnectionError("Failed to connect to Ollama")
            yield

        transport.stream_frames.side_effect = failing

        events = list(gateway.complete_stream_events(model="qwen3:32b", messages=messages, config=CompletionConfig()))

        assert events == [StreamError(reason=StreamErrorReason.REQUEST_FAILED, detail="Failed to connect to Ollama")]
