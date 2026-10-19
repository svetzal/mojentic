"""Public callers retain real SDK encoding under test-only offline enforcement."""

import inspect
import socket

import pytest

from mojentic.llm import CompletionConfig, LLMBroker, LLMMessage
from mojentic.llm.gateways.openai import OpenAIGateway
from scripts.inprocess_http import InProcessTokenizer, scripted_http


def broker(host: str) -> LLMBroker:
    return LLMBroker(
        model="gpt-4o",
        gateway=OpenAIGateway(api_key="credential-sentinel", base_url=host),
        tokenizer=InProcessTokenizer(),
    )


class DescribeOfflinePublicCalls:
    def should_preserve_native_socket_type_and_exact_sdk_exchange(self):
        response = (
            b'{"id":"chatcmpl-test","model":"gpt-4o","choices":'
            b'[{"index":0,"message":{"role":"assistant","content":"answer"},'
            b'"finish_reason":"stop"}]}'
        )
        request_id = "req_12345678-1234-4234-8234-123456789abc"
        with scripted_http([(200, {"x-request-id": request_id}, response)]) as (host, requests):
            result = broker(host).generate_response(
                [LLMMessage(content="hello")], config=CompletionConfig(temperature=0.25, max_tokens=17)
            )

            assert result.content == "answer"
            assert result.provider_metadata.request_id == request_id
            assert requests[0][0] == "/chat/completions"
            assert requests[0][1] == (
                b'{"messages":[{"role":"user","content":"hello"}],"model":"gpt-4o",'
                b'"max_tokens":17,"temperature":0.25}'
            )
            assert requests[0][2]["authorization"] == "Bearer credential-sentinel"
            assert inspect.ismethoddescriptor(socket.socket.__init__)
            assert inspect.ismethoddescriptor(socket.socket.connect)
            assert inspect.ismethoddescriptor(socket.socket.bind)

    def should_reject_an_unhandled_provider_route_before_io(self):
        with pytest.raises(Exception) as failure:
            broker("http://127.0.0.1:9").generate_response([LLMMessage(content="hello")])

        cause = failure.value
        while cause.__cause__ is not None:
            cause = cause.__cause__
        assert isinstance(cause, AssertionError)
        assert str(cause) == "Verification must not open sockets or resolve services"
