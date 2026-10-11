"""Strict structured tools through the SDK and owned loopback HTTP boundaries."""

import json

import httpx
import pytest

from mojentic.llm.chat_session import ChatSession
from mojentic.llm.completion_config import CompletionConfig
from mojentic.llm.gateways import omlx_recovery_spec as recovery_fixtures
from mojentic.llm.gateways.cloud_recovery_spec import OPENAI_BODY, RECOVERED
from mojentic.llm.gateways.models import LLMMessage
from mojentic.llm.gateways.ollama_recovery_spec import scripted_http
from mojentic.llm.gateways.omlx import OMLXGateway
from mojentic.llm.gateways.omlx_recovery_spec import (
    Result,
    allow,
    completion,
)
from mojentic.llm.gateways.openai import OpenAIGateway
from mojentic.llm.recovery import RecoveryError, RecoveryPolicy
from mojentic.llm.tools.llm_tool import LLMTool

broker_factory = recovery_fixtures.broker_factory


class StrictTool(LLMTool):
    """A real strict tool with observable execution count."""

    def __init__(self) -> None:
        super().__init__()
        self.calls = []

    @property
    def descriptor(self) -> dict:
        return {
            "type": "function",
            "function": {
                "name": "lookup",
                "description": "Lookup city",
                "strict": True,
                "parameters": {
                    "type": "object",
                    "properties": {"city": {"type": "string"}},
                    "required": ["city"],
                    "additionalProperties": False,
                },
            },
        }

    def run(self, city: str) -> str:
        self.calls.append(city)
        return city


TOOL_RESPONSE = (
    b'{"id":"chatcmpl-test","object":"chat.completion","created":1,"model":"gpt-4o",'
    b'"choices":[{"index":0,"finish_reason":"tool_calls","message":{"role":"assistant",'
    b'"content":null,"tool_calls":[{"id":"call-exact","type":"function",'
    b'"function":{"name":"lookup","arguments":"{\\"city\\":\\"Paris\\"}"}}]}}]}'
)
EXPECTED_BODY = (
    OPENAI_BODY
    + b',"response_format":{"type":"json_schema","json_schema":{"name":"Result","strict":true,"schema":'
    b'{"properties":{"answer":{"title":"Answer","type":"string"}},"required":["answer"],'
    b'"title":"Result","type":"object","additionalProperties":false}}},'
    b'"tools":[{"type":"function","function":{"name":"lookup","description":"Lookup city","strict":true,'
    b'"parameters":{"type":"object","properties":{"city":{"type":"string"}},"required":["city"],'
    b'"additionalProperties":false}}}]}'
)


def arguments() -> dict:
    """Return fresh caller inputs independent of the expected literal bytes."""
    return {
        "model": "gpt-4o",
        "messages": [LLMMessage(content="héllo")],
        "config": CompletionConfig(temperature=0.25, max_tokens=17),
        "object_model": Result,
        "tools": [StrictTool()],
    }


def assert_tool(result) -> None:
    """Assert the exact successful response contract."""
    assert result.content is None
    assert result.object is None
    assert [tool.model_dump() for tool in result.tool_calls] == [
        {"id": "call-exact", "name": "lookup", "arguments": {"city": "Paris"}}
    ]


class DescribeStrictStructuredToolRecovery:
    def should_characterize_sdk_public_completion(self):
        with scripted_http([(200, {}, TOOL_RESPONSE)]) as (host, requests):
            gateway = OpenAIGateway(api_key="loopback", base_url=host + "/v1")
            result = gateway.complete(**arguments())
            gateway.client.close()
        assert_tool(result)
        assert [path for path, _, _ in requests] == ["/v1/chat/completions"]
        assert [json.loads(body) for _, body, _ in requests] == [
            json.loads(EXPECTED_BODY) | {"stream": False}
        ]

    @pytest.mark.parametrize("recover", [False, True])
    async def should_retain_null_object_and_exact_tool_through_public_recovery(
        self, recover
    ):
        responses = [(503, {}, b"original failure")] * int(recover)
        responses += [(200, {}, TOOL_RESPONSE)]
        events, captures = [], []
        policy = RecoveryPolicy(
            max_attempts=2,
            base_delay=0,
            admission=allow,
            observer=events.append,
            wire_observer=captures.append,
        )
        with scripted_http(responses) as (host, requests):
            gateway = OpenAIGateway(
                api_key="loopback", base_url=host + "/v1", recovery_policy=policy
            )
            result = await gateway.complete_with_recovery(**arguments())
            gateway.client.close()
        assert_tool(result)
        count = 1 + int(recover)
        assert [(path, body) for path, body, _ in requests] == [
            ("/v1/chat/completions", EXPECTED_BODY)
        ] * count
        sends = [capture for capture in captures if capture.kind == "request"]
        assert [send.body for send in sends] == [EXPECTED_BODY] * count
        assert len({send.identity.attempt_id for send in sends}) == count
        assert {send.identity.logical_request_id for send in sends} == {
            result.recovery_report.identity.logical_request_id
        }
        assert [send.identity.wire_attempt for send in sends] == list(
            range(1, count + 1)
        )
        assert [event.transition for event in events] == (
            RECOVERED if recover else ["attempt_started", "attempt_succeeded"]
        )
        assert result.recovery_report.outcome == "succeeded"
        assert result.recovery_report.identity == sends[-1].identity
        assert {event.identity.logical_request_id for event in events} == {
            result.recovery_report.identity.logical_request_id
        }
        assert [
            event.identity for event in events if event.transition == "attempt_started"
        ] == [send.identity for send in sends]
        assert events[-1].identity == sends[-1].identity
        assert result.recovery_report.progress.delivered_tool_calls == 1
        assert [
            event.failure for event in events if event.transition == "attempt_failed"
        ] == list(result.recovery_report.history)
        assert len(result.recovery_report.history) == int(recover)
        for failure in result.recovery_report.history:
            assert failure.http_status == 503
            assert failure.identity == sends[0].identity
            assert isinstance(failure.inspect_cause(), httpx.HTTPStatusError)
            assert failure.inspect_cause().response.status_code == 503
            assert failure.inspect_response() == b"original failure"
        assert [
            capture.status for capture in captures if capture.kind == "headers"
        ] == [status for status, _, _ in responses]
        assert [capture.body for capture in captures if capture.kind == "body"] == [
            body for _, _, body in responses
        ]

    @pytest.mark.parametrize(
        "finish", ["stop", None, "unknown", "length", "content_filter"]
    )
    async def should_reject_null_tool_content_without_safe_tool_finish(self, finish):
        frame = json.loads(TOOL_RESPONSE)
        frame["choices"][0]["finish_reason"] = finish
        with scripted_http([(200, {}, json.dumps(frame).encode())]) as (host, requests):
            gateway = OpenAIGateway(
                api_key="loopback",
                base_url=host + "/v1",
                recovery_policy=RecoveryPolicy(max_attempts=3),
            )
            with pytest.raises(RecoveryError) as caught:
                await gateway.complete_with_recovery(**arguments())
            gateway.client.close()
        assert len(requests) == 1
        assert len(caught.value.report.history) == 1
        assert caught.value.report.history[0].category == "protocol"
        assert isinstance(caught.value.inspect_cause(), ValueError)

    @pytest.mark.parametrize("arguments_text", ["{", "[]", "null", '"Paris"'])
    async def should_reject_malformed_or_nonobject_tool_arguments(self, arguments_text):
        frame = json.loads(TOOL_RESPONSE)
        frame["choices"][0]["message"]["tool_calls"][0]["function"]["arguments"] = (
            arguments_text
        )
        with scripted_http([(200, {}, json.dumps(frame).encode())]) as (host, requests):
            gateway = OpenAIGateway(
                api_key="loopback",
                base_url=host + "/v1",
                recovery_policy=RecoveryPolicy(max_attempts=3),
            )
            with pytest.raises(RecoveryError) as caught:
                await gateway.complete_with_recovery(**arguments())
            gateway.client.close()
        assert len(requests) == 1
        assert isinstance(caught.value.inspect_cause(), (ValueError, TypeError))
        assert caught.value.report.history[0].category == "protocol"

    @pytest.mark.parametrize("content", ["not JSON", '{"wrong":"value"}', ""])
    async def should_validate_nonnull_structured_content_even_with_tools(self, content):
        frame = json.loads(TOOL_RESPONSE)
        frame["choices"][0]["message"]["content"] = content
        with scripted_http([(200, {}, json.dumps(frame).encode())]) as (host, requests):
            gateway = OpenAIGateway(
                api_key="loopback",
                base_url=host + "/v1",
                recovery_policy=RecoveryPolicy(max_attempts=3),
            )
            with pytest.raises(RecoveryError) as caught:
                await gateway.complete_with_recovery(**arguments())
            gateway.client.close()
        assert len(requests) == 1
        assert isinstance(caught.value.inspect_cause(), ValueError)
        assert caught.value.report.history[0].category == "protocol"

    @pytest.mark.parametrize("tools", [None, []])
    async def should_reject_null_content_without_tools(self, tools):
        frame = json.loads(TOOL_RESPONSE)
        frame["choices"][0]["message"]["tool_calls"] = tools
        with scripted_http([(200, {}, json.dumps(frame).encode())]) as (host, requests):
            gateway = OpenAIGateway(
                api_key="loopback",
                base_url=host + "/v1",
                recovery_policy=RecoveryPolicy(max_attempts=3),
            )
            with pytest.raises(RecoveryError) as caught:
                await gateway.complete_with_recovery(**arguments())
            gateway.client.close()
        assert len(requests) == 1
        assert isinstance(caught.value.inspect_cause(), ValueError)

    async def should_reject_nonstrict_tools_before_dispatch(self):
        class NonStrictTool(StrictTool):
            @property
            def descriptor(self) -> dict:
                descriptor = super().descriptor
                descriptor["function"]["strict"] = False
                return descriptor

        args = arguments() | {"tools": [NonStrictTool()]}
        with scripted_http([]) as (host, requests):
            gateway = OpenAIGateway(
                api_key="loopback",
                base_url=host + "/v1",
                recovery_policy=RecoveryPolicy(max_attempts=3),
            )
            with pytest.raises(RecoveryError) as caught:
                await gateway.complete_with_recovery(**args)
            gateway.client.close()
        assert requests == []
        assert caught.value.report.history == ()
        assert isinstance(caught.value.inspect_cause(), ValueError)

    async def should_preserve_omlx_structured_tool_only_rejection(self):
        with scripted_http([(200, {}, TOOL_RESPONSE)]) as (host, requests):
            gateway = OMLXGateway(
                host=host, recovery_policy=RecoveryPolicy(max_attempts=3)
            )
            with pytest.raises(RecoveryError) as caught:
                await gateway.complete_with_recovery(**arguments())
        assert isinstance(caught.value.inspect_cause(), ValueError)
        assert len(requests) == 1

    async def should_preserve_omlx_ordinary_tool_only_success(self):
        with scripted_http([(200, {}, TOOL_RESPONSE)]) as (host, requests):
            gateway = OMLXGateway(
                host=host, recovery_policy=RecoveryPolicy(max_attempts=3)
            )
            result = await gateway.complete_with_recovery(
                **(arguments() | {"object_model": None})
            )
        assert_tool(result)
        assert len(requests) == 1

    def should_return_tool_without_execution_through_public_broker_response(
        self, broker_factory
    ):
        tool = StrictTool()
        with scripted_http([(200, {}, TOOL_RESPONSE)]) as (host, requests):
            gateway = OpenAIGateway(
                api_key="loopback",
                base_url=host + "/v1",
                recovery_policy=RecoveryPolicy(),
            )
            broker = broker_factory(gateway)
            result = broker.generate_response(
                [LLMMessage(content="héllo")], tools=[tool]
            )
            gateway.client.close()
        assert_tool(result)
        assert tool.calls == []
        assert len(requests) == 1

    @pytest.mark.parametrize("entrypoint", ["generate", "send"])
    def should_execute_tool_once_through_supported_public_callers(
        self, entrypoint, broker_factory
    ):
        tool = StrictTool()
        final = completion("done").replace(
            b'"finish_reason": "length"', b'"finish_reason": "stop"'
        )
        with scripted_http(
            [(200, {}, TOOL_RESPONSE), (503, {}, b"private"), (200, {}, final)]
        ) as (host, requests):
            gateway = OpenAIGateway(
                api_key="loopback",
                base_url=host + "/v1",
                recovery_policy=RecoveryPolicy(max_attempts=2, base_delay=0),
            )
            broker = broker_factory(gateway)
            session = ChatSession(
                broker, tools=[tool], tokenizer_gateway=broker.tokenizer
            )
            result = {
                "generate": lambda: broker.generate(
                    [LLMMessage(content="héllo")], tools=[tool]
                ),
                "send": lambda: session.send("héllo"),
            }[entrypoint]()
            gateway.client.close()
        assert result == "done"
        assert tool.calls == ["Paris"]
        assert len(requests) == 3
        assert requests[1][1] == requests[2][1]
        history = json.loads(requests[1][1])["messages"]
        assert [
            message["tool_calls"][0]["id"]
            for message in history
            if message.get("tool_calls")
        ] == ["call-exact"]
        assert [
            message["tool_call_id"] for message in history if message["role"] == "tool"
        ] == ["call-exact"]
