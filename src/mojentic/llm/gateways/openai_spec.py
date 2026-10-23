import json
import math

import httpx
import pytest
from openai import APIStatusError, OpenAI

from mojentic.llm.completion_config import CompletionConfig, ResponseFormat
from mojentic.llm.gateways.models import LLMMessage, MessageRole
from mojentic.llm.gateways.openai import OpenAIGateway
from mojentic.llm.gateways.stream_events import (
    StreamCompleted,
    StreamContent,
    StreamError,
    StreamErrorReason,
)
from scripts.inprocess_http import InProcessTokenizer


class DescribeOpenAIGateway:
    """
    Unit tests for the OpenAI gateway
    """

    class DescribeInitialization:
        @pytest.mark.parametrize("explicit_key", [None, "explicit-key"])
        @pytest.mark.parametrize("explicit_host", [False, True])
        def should_apply_environment_and_explicit_settings_at_dispatch(
            self, monkeypatch, explicit_key, explicit_host
        ):
            from mojentic.llm.gateways.ollama_recovery_spec import scripted_http
            from mojentic.llm.gateways.request_fidelity_spec import reply

            with scripted_http([(200, {}, reply("openai", "events"))]) as (
                host,
                requests,
            ):
                monkeypatch.setenv("OPENAI_API_KEY", "environment-key")
                monkeypatch.setenv("OPENAI_API_ENDPOINT", host + "/v1")
                base_url = host + "/explicit" if explicit_host else None
                gateway = OpenAIGateway(api_key=explicit_key, base_url=base_url)
                terminal = list(
                    gateway.complete_stream_events(
                        "gpt-4o", [LLMMessage(content="hello")], CompletionConfig()
                    )
                )[-1]

            assert terminal.type == "completed"
            assert terminal.metadata.first_token_kind == "content"
            assert (
                requests[0][0]
                == {False: "/v1/chat/completions", True: "/explicit/chat/completions"}[
                    explicit_host
                ]
            )
            assert requests[0][2]["authorization"] == "Bearer " + (
                explicit_key or "environment-key"
            )

        def should_use_default_endpoint_when_unspecified(self, monkeypatch):
            monkeypatch.delenv("OPENAI_API_ENDPOINT", raising=False)
            monkeypatch.delenv("OPENAI_BASE_URL", raising=False)

            gateway = OpenAIGateway(api_key="test-key")

            assert str(gateway.client.base_url) == "https://api.openai.com/v1/"


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
        mocker.patch("mojentic.llm.gateways.openai.OpenAI")
        return OpenAIGateway(api_key="k", stream_transport=transport)

    @pytest.fixture
    def messages(self):
        return [LLMMessage(role=MessageRole.User, content="Hi")]

    def should_send_one_streaming_request_with_usage_and_no_tools(
        self, gateway, transport, messages
    ):
        transport.stream_lines.return_value = _generator([])
        config = CompletionConfig(response_format=ResponseFormat(type="json_object"))

        list(
            gateway.complete_stream_events(
                model="gpt-4o", messages=messages, config=config
            )
        )

        body = transport.stream_lines.call_args.args[0]
        assert (
            transport.stream_lines.call_count,
            body["stream"],
            body["stream_options"],
            body["response_format"],
            "tools" in body,
        ) == (1, True, {"include_usage": True}, {"type": "json_object"}, False)

    def should_parse_the_provider_stream_into_events(
        self, gateway, transport, messages
    ):
        transport.stream_lines.return_value = _generator(
            [
                'data: {"model":"gpt-4o","choices":[{"delta":{"content":"Hi"},"finish_reason":"stop"}]}',
                "data: [DONE]",
            ]
        )

        events = list(
            gateway.complete_stream_events(
                model="gpt-4o", messages=messages, config=CompletionConfig()
            )
        )

        assert [type(event) for event in events] == [StreamContent, StreamCompleted]

    def should_close_the_request_after_the_terminal_event(
        self, gateway, transport, messages
    ):
        closed = []
        transport.stream_lines.return_value = _tracked(iter(["data: [DONE]"]), closed)

        list(
            gateway.complete_stream_events(
                model="gpt-4o", messages=messages, config=CompletionConfig()
            )
        )

        assert closed == [True]

    def should_report_http_error_status_as_provider_error(
        self, gateway, transport, messages
    ):
        def failing(body):
            request = httpx.Request(
                "POST", "https://api.openai.com/v1/chat/completions"
            )
            raise APIStatusError(
                "rate limited",
                response=httpx.Response(429, request=request),
                body={"message": "rate limited"},
            )
            yield

        transport.stream_lines.side_effect = failing

        events = list(
            gateway.complete_stream_events(
                model="gpt-4o", messages=messages, config=CompletionConfig()
            )
        )

        assert events == [
            StreamError(
                reason=StreamErrorReason.PROVIDER_ERROR,
                detail={"status_code": 429, "error": {"message": "rate limited"}},
            )
        ]

    def should_report_transport_failure_as_request_failed(
        self, gateway, transport, messages
    ):
        def failing(body):
            yield 'data: {"choices":[{"delta":{"content":"Hi"}}]}'
            raise httpx.ReadError("connection reset")

        transport.stream_lines.side_effect = failing

        events = list(
            gateway.complete_stream_events(
                model="gpt-4o", messages=messages, config=CompletionConfig()
            )
        )

        assert events[-1] == StreamError(
            reason=StreamErrorReason.REQUEST_FAILED, detail="connection reset"
        )

    def should_report_models_without_streaming_as_unsupported_without_a_request(
        self, gateway, transport, messages
    ):
        events = list(
            gateway.complete_stream_events(
                model="gpt-5-pro", messages=messages, config=CompletionConfig()
            )
        )

        assert (
            [event.reason for event in events],
            transport.stream_lines.call_count,
        ) == ([StreamErrorReason.STREAM_EVENTS_UNSUPPORTED], 0)


class DescribeOpenAIEmbeddings:
    def should_weight_parts_by_token_count_before_normalizing(self):
        token_counts = []

        def respond(request):
            tokens = json.loads(request.content)["input"]
            token_counts.append(len(tokens))
            vector = [1.0, 0.0] if len(tokens) == 8191 else [0.0, 1.0]
            return httpx.Response(
                200,
                json={
                    "object": "list",
                    "data": [{"object": "embedding", "index": 0, "embedding": vector}],
                    "model": "text-embedding-3-large",
                    "usage": {
                        "prompt_tokens": len(tokens),
                        "total_tokens": len(tokens),
                    },
                },
            )

        gateway = OpenAIGateway(api_key="test-key")
        gateway.client.close()
        with OpenAI(
            api_key="test-key",
            http_client=httpx.Client(transport=httpx.MockTransport(respond)),
        ) as client:
            gateway.client = client
            gateway._embedding_tokenizer = InProcessTokenizer()
            result = gateway.calculate_embeddings("w" * 8291)

        norm = math.hypot(8191, 100)
        assert result == pytest.approx([8191 / norm, 100 / norm])
        assert token_counts == [8191, 100]
        assert math.hypot(*result) == pytest.approx(1.0)
