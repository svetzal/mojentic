"""Public callers retain real SDK encoding under test-only offline enforcement."""

from contextlib import ExitStack

import pytest

from mojentic.llm import CompletionConfig, LLMBroker, LLMMessage
from mojentic.llm.gateways.openai import OpenAIGateway
from mojentic.llm.recovery import RecoveryPolicy
from scripts.inprocess_http import InProcessTokenizer, offline, scripted_http

RESPONSE = (
    b'{"id":"chatcmpl-test","model":"gpt-4o","choices":'
    b'[{"index":0,"message":{"role":"assistant","content":"answer"},'
    b'"finish_reason":"stop"}]}'
)


def broker(host: str, policy: RecoveryPolicy | None = None) -> LLMBroker:
    return LLMBroker(
        model="gpt-4o",
        gateway=OpenAIGateway(
            api_key="credential-sentinel", base_url=host, recovery_policy=policy
        ),
        tokenizer=InProcessTokenizer(),
    )


class DescribeOfflinePublicCalls:
    def should_preserve_exact_recovery_exchange_and_request_identity(self):
        request_id = "req_12345678-1234-4234-8234-123456789abc"
        wire = []
        with scripted_http([(200, {"x-request-id": request_id}, RESPONSE)]) as (
            host,
            requests,
        ):
            result = broker(
                host, RecoveryPolicy(wire_observer=wire.append)
            ).generate_response(
                [LLMMessage(content="hello")],
                config=CompletionConfig(temperature=0.25, max_tokens=17),
            )

            assert result.content == "answer"
            headers = next(event for event in wire if event.kind == "headers")
            assert ("x-request-id", request_id) in headers.headers
            assert (
                headers.identity.logical_request_id
                == result.recovery_report.identity.logical_request_id
            )
            assert requests[0][0] == "/chat/completions"
            assert requests[0][1] == (
                b'{"model":"gpt-4o","messages":[{"role":"user","content":"hello"}],'
                b'"temperature":0.25,"max_tokens":17}'
            )
            assert requests[0][2]["authorization"] == "Bearer credential-sentinel"

    def should_preserve_exact_sdk_serialization_and_authorization(self):
        with scripted_http([(200, {}, RESPONSE)]) as (host, requests):
            result = broker(host).generate_response(
                [LLMMessage(content="hello")],
                config=CompletionConfig(temperature=0.25, max_tokens=17),
            )

        assert result.content == "answer"
        assert len(requests) == 1
        assert requests[0][0] == "/chat/completions"
        assert requests[0][1] == (
            b'{"model":"gpt-4o","messages":[{"role":"user","content":"hello"}],'
            b'"max_tokens":17,"temperature":0.25}'
        )
        assert requests[0][2]["authorization"] == "Bearer credential-sentinel"

    @pytest.mark.parametrize("depth", [0, 1, 2])
    def should_reject_an_unhandled_provider_route_before_io(self, depth):
        with ExitStack() as stack:
            for _ in range(depth):
                stack.enter_context(offline())
            with pytest.raises(ValueError, match="unwind nested guard"), offline():
                raise ValueError("unwind nested guard")

        with pytest.raises(Exception) as failure:
            broker("http://provider.test").generate_response(
                [LLMMessage(content="hello")]
            )

        cause = failure.value
        while cause.__cause__ is not None:
            cause = cause.__cause__
        assert isinstance(cause, AssertionError)
        assert str(cause) == "Verification must not open sockets or resolve services"

    def should_restore_outer_transport_after_inner_context_exits(self):
        with scripted_http([(200, {}, RESPONSE), (200, {}, RESPONSE)]) as (
            host,
            requests,
        ):
            first = broker(host).generate_response([LLMMessage(content="hello")])
            with scripted_http([(200, {}, RESPONSE)]) as (inner_host, inner_requests):
                inner = broker(inner_host).generate_response(
                    [LLMMessage(content="inner")]
                )
            last = broker(host).generate_response([LLMMessage(content="again")])

        assert [first.content, inner.content, last.content] == [
            "answer",
            "answer",
            "answer",
        ]
        assert len(requests) == 2
        assert len(inner_requests) == 1

    def should_reject_unhandled_route_after_scripted_transport_exits(self):
        with scripted_http([(200, {}, RESPONSE)]) as (host, requests):
            result = broker(host).generate_response([LLMMessage(content="hello")])

        with pytest.raises(Exception) as failure:
            broker(host).generate_response([LLMMessage(content="hello")])

        assert result.content == "answer"
        assert len(requests) == 1
        cause = failure.value
        while cause.__cause__ is not None:
            cause = cause.__cause__
        assert isinstance(cause, AssertionError)
        assert str(cause) == "Verification must not open sockets or resolve services"
