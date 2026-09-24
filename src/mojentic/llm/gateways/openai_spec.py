import os
from unittest.mock import patch

import httpx
import pytest
from openai import APIStatusError

from mojentic.llm.completion_config import CompletionConfig, ResponseFormat
from mojentic.llm.gateways.stream_events import StreamCompleted, StreamContent, StreamError, StreamErrorReason
from mojentic.llm.gateways.models import LLMMessage, MessageRole
from mojentic.llm.gateways.openai import OpenAIGateway


class DescribeOpenAIGateway:
    """
    Unit tests for the OpenAI gateway
    """

    class DescribeInitialization:
        """
        Tests for OpenAI gateway initialization
        """

        def should_initialize_with_api_key(self, mocker):
            api_key = "test-api-key"
            mock_openai = mocker.patch('mojentic.llm.gateways.openai.OpenAI')

            gateway = OpenAIGateway(api_key=api_key)

            mock_openai.assert_called_once_with(api_key=api_key, base_url=None)
            assert gateway.client is not None

        def should_initialize_with_api_key_and_base_url(self, mocker):
            api_key = "test-api-key"
            base_url = "https://custom.openai.com"
            mock_openai = mocker.patch('mojentic.llm.gateways.openai.OpenAI')

            gateway = OpenAIGateway(api_key=api_key, base_url=base_url)

            mock_openai.assert_called_once_with(api_key=api_key, base_url=base_url)
            assert gateway.client is not None

        def should_read_api_key_from_environment_variable(self, mocker):
            api_key = "test-api-key-from-env"
            mock_openai = mocker.patch('mojentic.llm.gateways.openai.OpenAI')

            with patch.dict(os.environ, {'OPENAI_API_KEY': api_key}):
                gateway = OpenAIGateway()

            mock_openai.assert_called_once_with(api_key=api_key, base_url=None)
            assert gateway.client is not None

        def should_read_base_url_from_environment_variable(self, mocker):
            api_key = "test-api-key"
            endpoint = "https://corporate.openai.com"
            mock_openai = mocker.patch('mojentic.llm.gateways.openai.OpenAI')

            with patch.dict(os.environ, {'OPENAI_API_ENDPOINT': endpoint}):
                gateway = OpenAIGateway(api_key=api_key)

            mock_openai.assert_called_once_with(api_key=api_key, base_url=endpoint)
            assert gateway.client is not None

        def should_read_both_from_environment_variables(self, mocker):
            api_key = "test-api-key-from-env"
            endpoint = "https://corporate.openai.com"
            mock_openai = mocker.patch('mojentic.llm.gateways.openai.OpenAI')

            with patch.dict(os.environ, {'OPENAI_API_KEY': api_key, 'OPENAI_API_ENDPOINT': endpoint}):
                gateway = OpenAIGateway()

            mock_openai.assert_called_once_with(api_key=api_key, base_url=endpoint)
            assert gateway.client is not None

        def should_prefer_explicit_api_key_over_environment_variable(self, mocker):
            api_key_env = "test-api-key-from-env"
            api_key_explicit = "test-api-key-explicit"
            mock_openai = mocker.patch('mojentic.llm.gateways.openai.OpenAI')

            with patch.dict(os.environ, {'OPENAI_API_KEY': api_key_env}):
                gateway = OpenAIGateway(api_key=api_key_explicit)

            mock_openai.assert_called_once_with(api_key=api_key_explicit, base_url=None)
            assert gateway.client is not None

        def should_prefer_explicit_base_url_over_environment_variable(self, mocker):
            api_key = "test-api-key"
            endpoint_env = "https://corporate.openai.com"
            endpoint_explicit = "https://explicit.openai.com"
            mock_openai = mocker.patch('mojentic.llm.gateways.openai.OpenAI')

            with patch.dict(os.environ, {'OPENAI_API_ENDPOINT': endpoint_env}):
                gateway = OpenAIGateway(api_key=api_key, base_url=endpoint_explicit)

            mock_openai.assert_called_once_with(api_key=api_key, base_url=endpoint_explicit)
            assert gateway.client is not None

        def should_use_none_when_no_endpoint_specified(self, mocker):
            api_key = "test-api-key"
            mock_openai = mocker.patch('mojentic.llm.gateways.openai.OpenAI')

            with patch.dict(os.environ, {}, clear=True):
                gateway = OpenAIGateway(api_key=api_key)

            mock_openai.assert_called_once_with(api_key=api_key, base_url=None)
            assert gateway.client is not None


def _generator(items):
    yield from items


def _tracked(lines, closed):
    try:
        yield from lines
    finally:
        closed.append(True)


class DescribeStreamEvents:

    @pytest.fixture
    def transport(self, mocker):
        from mojentic.llm.gateways.openai import OpenAIStreamTransport
        return mocker.Mock(spec=OpenAIStreamTransport)

    @pytest.fixture
    def gateway(self, mocker, transport):
        mocker.patch('mojentic.llm.gateways.openai.OpenAI')
        return OpenAIGateway(api_key="k", stream_transport=transport)

    @pytest.fixture
    def messages(self):
        return [LLMMessage(role=MessageRole.User, content="Hi")]

    def should_send_one_streaming_request_with_usage_and_no_tools(self, gateway, transport, messages):
        transport.stream_lines.return_value = _generator([])
        config = CompletionConfig(response_format=ResponseFormat(type="json_object"))

        list(gateway.complete_stream_events(model="gpt-4o", messages=messages, config=config))

        body = transport.stream_lines.call_args.args[0]
        assert (transport.stream_lines.call_count, body["stream"], body["stream_options"],
                body["response_format"], "tools" in body) == (
            1, True, {"include_usage": True}, {"type": "json_object"}, False)

    def should_parse_the_provider_stream_into_events(self, gateway, transport, messages):
        transport.stream_lines.return_value = _generator([
            'data: {"model":"gpt-4o","choices":[{"delta":{"content":"Hi"},"finish_reason":"stop"}]}',
            "data: [DONE]",
        ])

        events = list(gateway.complete_stream_events(model="gpt-4o", messages=messages, config=CompletionConfig()))

        assert [type(event) for event in events] == [StreamContent, StreamCompleted]

    def should_close_the_request_after_the_terminal_event(self, gateway, transport, messages):
        closed = []
        transport.stream_lines.return_value = _tracked(iter(["data: [DONE]"]), closed)

        list(gateway.complete_stream_events(model="gpt-4o", messages=messages, config=CompletionConfig()))

        assert closed == [True]

    def should_report_http_error_status_as_provider_error(self, gateway, transport, messages):
        def failing(body):
            request = httpx.Request("POST", "https://api.openai.com/v1/chat/completions")
            raise APIStatusError("rate limited", response=httpx.Response(429, request=request),
                                 body={"message": "rate limited"})
            yield

        transport.stream_lines.side_effect = failing

        events = list(gateway.complete_stream_events(model="gpt-4o", messages=messages, config=CompletionConfig()))

        assert events == [StreamError(reason=StreamErrorReason.PROVIDER_ERROR,
                                      detail={"status_code": 429, "error": {"message": "rate limited"}})]

    def should_report_transport_failure_as_request_failed(self, gateway, transport, messages):
        def failing(body):
            yield 'data: {"choices":[{"delta":{"content":"Hi"}}]}'
            raise httpx.ReadError("connection reset")

        transport.stream_lines.side_effect = failing

        events = list(gateway.complete_stream_events(model="gpt-4o", messages=messages, config=CompletionConfig()))

        assert events[-1] == StreamError(reason=StreamErrorReason.REQUEST_FAILED, detail="connection reset")

    def should_report_models_without_streaming_as_unsupported_without_a_request(self, gateway, transport, messages):
        events = list(gateway.complete_stream_events(model="gpt-5-pro", messages=messages, config=CompletionConfig()))

        assert ([event.reason for event in events], transport.stream_lines.call_count) == (
            [StreamErrorReason.STREAM_EVENTS_UNSUPPORTED], 0)
