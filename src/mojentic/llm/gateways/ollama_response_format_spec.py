import pytest
from ollama import ChatResponse, Message

from mojentic.llm.completion_config import CompletionConfig, ResponseFormat
from mojentic.llm.gateways.models import LLMMessage, MessageRole
from mojentic.llm.gateways.ollama import OllamaGateway, ollama_format

SCHEMA = {"type": "object", "properties": {"answer": {"type": "string"}}}

FORMAT_CASES = [
    (ResponseFormat(type="json_object"), "json"),
    (ResponseFormat(type="json_object", json_schema=SCHEMA), SCHEMA),
]


@pytest.fixture
def mock_ollama_client(mocker):
    return mocker.MagicMock()


@pytest.fixture
def gateway(mocker, mock_ollama_client):
    mocker.patch('mojentic.llm.gateways.ollama.Client', return_value=mock_ollama_client)
    return OllamaGateway()


@pytest.fixture
def messages():
    return [LLMMessage(role=MessageRole.User, content="Reply in JSON")]


class DescribeOllamaResponseFormat:

    @pytest.mark.parametrize("response_format,expected", FORMAT_CASES)
    def should_map_json_formats_to_ollama_format(self, response_format, expected):
        assert ollama_format(response_format) == expected

    @pytest.mark.parametrize("response_format", [None, ResponseFormat(type="text")])
    def should_omit_format_for_text_or_absent(self, response_format):
        assert ollama_format(response_format) is None

    class DescribeStreamingRequests:

        @pytest.mark.parametrize("response_format,expected", FORMAT_CASES)
        def should_forward_configured_format(self, gateway, mock_ollama_client, messages,
                                             response_format, expected):
            mock_ollama_client.chat.return_value = iter([])
            config = CompletionConfig(response_format=response_format)

            list(gateway.complete_stream(model="qwen3", messages=messages, config=config))

            assert mock_ollama_client.chat.call_args.kwargs["format"] == expected

        @pytest.mark.parametrize("response_format", [None, ResponseFormat(type="text")])
        def should_leave_body_unchanged_for_text_or_absent(self, gateway, mock_ollama_client, messages,
                                                           response_format):
            mock_ollama_client.chat.return_value = iter([])
            config = CompletionConfig(response_format=response_format)

            list(gateway.complete_stream(model="qwen3", messages=messages, config=config))

            assert "format" not in mock_ollama_client.chat.call_args.kwargs

    class DescribeNonStreamingRequests:

        @pytest.mark.parametrize("response_format,expected", FORMAT_CASES)
        def should_forward_configured_format(self, gateway, mock_ollama_client, messages,
                                             response_format, expected):
            mock_ollama_client.chat.return_value = ChatResponse(
                model="qwen3", done=True, message=Message(role="assistant", content="{}"))
            config = CompletionConfig(response_format=response_format)

            gateway.complete(model="qwen3", messages=messages, config=config)

            assert mock_ollama_client.chat.call_args.kwargs["format"] == expected
