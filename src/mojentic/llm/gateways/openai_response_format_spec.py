import pytest
from unittest.mock import MagicMock

from mojentic.llm.completion_config import CompletionConfig, ResponseFormat
from mojentic.llm.gateways.models import LLMMessage, MessageRole
from mojentic.llm.gateways.openai import OpenAIGateway, openai_response_format

SCHEMA = {"type": "object", "properties": {"answer": {"type": "string"}}}

FORMAT_CASES = [
    (ResponseFormat(type="text"), {"type": "text"}),
    (ResponseFormat(type="json_object"), {"type": "json_object"}),
    (ResponseFormat(type="json_object", json_schema=SCHEMA),
     {"type": "json_schema", "json_schema": {"name": "response", "schema": SCHEMA}}),
]


@pytest.fixture
def mock_openai_client():
    client = MagicMock()
    client.chat.completions.create.return_value = iter([])
    return client


@pytest.fixture
def gateway(mocker, mock_openai_client):
    mocker.patch('mojentic.llm.gateways.openai.OpenAI', return_value=mock_openai_client)
    return OpenAIGateway(api_key="test_key")


@pytest.fixture
def messages():
    return [LLMMessage(role=MessageRole.User, content="Reply in JSON")]


def _completion_response():
    response = MagicMock()
    response.choices = [MagicMock()]
    response.choices[0].message.content = "{}"
    response.choices[0].message.tool_calls = None
    response.choices[0].finish_reason = "stop"
    response.usage = None
    response.model = "gpt-4o-2024-08-06"
    return response


class DescribeOpenAIResponseFormat:

    @pytest.mark.parametrize("response_format,expected", FORMAT_CASES)
    def should_map_each_format_to_openai_request_shape(self, response_format, expected):
        assert openai_response_format(response_format) == expected

    def should_map_absent_format_to_none(self):
        assert openai_response_format(None) is None

    class DescribeStreamingRequests:

        @pytest.mark.parametrize("response_format,expected", FORMAT_CASES)
        def should_forward_configured_format(self, gateway, mock_openai_client, messages,
                                             response_format, expected):
            config = CompletionConfig(response_format=response_format)

            list(gateway.complete_stream(model="gpt-4o", messages=messages, config=config))

            assert mock_openai_client.chat.completions.create.call_args.kwargs["response_format"] == expected

        def should_leave_body_unchanged_without_format(self, gateway, mock_openai_client, messages):
            list(gateway.complete_stream(model="gpt-4o", messages=messages, config=CompletionConfig()))

            assert "response_format" not in mock_openai_client.chat.completions.create.call_args.kwargs

    class DescribeNonStreamingRequests:

        @pytest.mark.parametrize("response_format,expected", FORMAT_CASES)
        def should_forward_configured_format(self, gateway, mock_openai_client, messages,
                                             response_format, expected):
            mock_openai_client.chat.completions.create.return_value = _completion_response()
            config = CompletionConfig(response_format=response_format)

            gateway.complete(model="gpt-4o", messages=messages, config=config)

            assert mock_openai_client.chat.completions.create.call_args.kwargs["response_format"] == expected

        def should_leave_body_unchanged_without_format(self, gateway, mock_openai_client, messages):
            mock_openai_client.chat.completions.create.return_value = _completion_response()

            gateway.complete(model="gpt-4o", messages=messages, config=CompletionConfig())

            assert "response_format" not in mock_openai_client.chat.completions.create.call_args.kwargs
