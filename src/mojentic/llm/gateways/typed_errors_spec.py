"""python-typed-errors-v1: public errors at the real HTTP boundary."""

import asyncio
import json
import traceback

import httpx
import pytest

from mojentic.llm.chat_session import ChatSession
from mojentic.llm.completion_config import CompletionConfig
from mojentic.llm.gateways.anthropic import AnthropicGateway
from mojentic.llm.gateways.models import LLMMessage
from mojentic.llm.gateways.ollama import OllamaGateway
from mojentic.llm.gateways.ollama_recovery_spec import scripted_http
from mojentic.llm.gateways.omlx import OMLXGateway
from mojentic.llm.gateways.omlx_recovery_spec import Result, allow, completion
from mojentic.llm.gateways.omlx_recovery_spec import (
    broker_factory as shared_broker_factory,
)
from mojentic.llm.gateways.openai import OpenAIGateway
from mojentic.llm.recovery import (
    CaptureError,
    LengthTerminationError,
    RecoveryError,
    RecoveryPolicy,
    RecoveryPolicyError,
)
from scripts.inprocess_http import clock, virtual_sleep

broker_factory = shared_broker_factory
SECRET = "sentinel"
PROVIDERS = ["ollama", "omlx", "openai", "anthropic"]
OPERATIONS = [
    (provider, operation)
    for provider in PROVIDERS
    for operation in (
        ["ordinary"]
        if provider == "anthropic"
        else ["ordinary", "structured", "streaming"]
    )
]
CALLERS = [
    (provider, operation, entrypoint)
    for provider, operation in OPERATIONS
    for entrypoint in (
        ["gateway", "async", "broker"]
        if operation == "structured"
        else ["gateway", "async", "broker", "session"]
    )
]
CONFIG = CompletionConfig(temperature=0.25, num_ctx=32768, max_tokens=17)


def gateway_for(provider, host, policy):
    gateways = {
        "ollama": lambda: OllamaGateway(host=host, recovery_policy=policy),
        "omlx": lambda: OMLXGateway(host=host, recovery_policy=policy),
        "openai": lambda: OpenAIGateway(
            api_key=SECRET, base_url=host + "/v1", recovery_policy=policy
        ),
        "anthropic": lambda: AnthropicGateway(
            api_key=SECRET, base_url=host, recovery_policy=policy
        ),
    }
    return gateways[provider]()


def response_body(provider, operation, finish="stop"):
    if provider == "anthropic":
        return (
            b'{"id":"msg","type":"message","role":"assistant","model":"reported",'
            b'"content":[{"type":"text","text":"sentinel"}],"stop_reason":"end_turn",'
            b'"usage":{"input_tokens":2,"output_tokens":3}}'
        )
    if provider == "ollama":
        return (
            json.dumps(
                {
                    "model": "reported",
                    "message": {"role": "assistant", "content": "sentinel"},
                    "done": True,
                    "done_reason": finish,
                }
            ).encode()
            + b"\n"
        )
    if operation == "streaming":
        return (
            b'data: {"choices":[{"delta":{"content":"sentinel"}}]}\n\n'
            + b'data: {"choices":[{"delta":{},"finish_reason":"'
            + finish.encode()
            + b'"}]}\n\ndata: [DONE]\n\n'
        )
    return completion("sentinel").replace(
        b'"finish_reason": "length"', b'"finish_reason": "stop"'
    )


def expected_request(provider, operation, entrypoint):
    messages = [{"role": "user", "content": "prompt"}]
    if entrypoint == "session":
        messages.insert(0, {"role": "system", "content": "system"})
    payload = {"model": "test", "messages": messages}
    if provider == "ollama":
        payload["options"] = {"num_ctx": 32768, "num_predict": 17, "temperature": 0.25}
        if operation == "structured":
            payload["format"] = Result.model_json_schema()
        payload["stream"] = operation == "streaming"
    elif provider == "anthropic":
        payload = {
            "model": "test",
            "system": "system" if entrypoint == "session" else None,
            "messages": [{"role": "user", "content": "prompt"}],
            "temperature": 0.25,
            "max_tokens": 17,
        }
    else:
        payload |= {"temperature": 0.25, "max_tokens": 17}
        if operation == "structured":
            schema = Result.model_json_schema()
            name = "response"
            if provider == "openai":
                name = "Result"
                schema["additionalProperties"] = False
            payload["response_format"] = {
                "type": "json_schema",
                "json_schema": {"name": name},
            }
            if provider == "openai":
                payload["response_format"]["json_schema"]["strict"] = True
            payload["response_format"]["json_schema"]["schema"] = schema
        if operation == "streaming":
            payload |= {"stream": True, "stream_options": {"include_usage": True}}
    path = {"ollama": "/api/chat", "anthropic": "/v1/messages"}.get(
        provider, "/v1/chat/completions"
    )
    return path, json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode()


async def async_request(gateway, operation, args):
    if operation != "streaming":
        return await gateway.complete_with_recovery(**args)
    events = [event async for event in gateway.complete_stream_with_recovery(**args)]
    raise events[-1].error


def public_request(gateway, operation, entrypoint, broker, session):
    args = {
        "model": "test",
        "messages": [LLMMessage(content="prompt")],
        "config": CONFIG,
    }
    if operation == "structured":
        args["object_model"] = Result
    actions = {
        "gateway": lambda: (
            list(gateway.complete_stream(**args))
            if operation == "streaming"
            else gateway.complete(**args)
        ),
        "async": lambda: asyncio.run(async_request(gateway, operation, args)),
        "broker": lambda: broker.generate(args["messages"], config=CONFIG),
        "session": lambda: session.send("prompt"),
    }
    if operation == "structured":
        actions["broker"] = lambda: broker.generate_object(
            args["messages"], Result, config=CONFIG
        )
    if operation == "streaming":
        actions["broker"] = lambda: list(
            broker.generate_stream(args["messages"], config=CONFIG)
        )
        actions["session"] = lambda: list(session.send_stream("prompt"))
    return actions[entrypoint]()


class DescribeTypedErrorsV1:
    async def should_preserve_typed_length_after_delivered_openai_content(self):
        body = (
            b'data: {"choices":[{"delta":{"content":"sentinel"}}]}\n\n'
            b'data: {"choices":[{"delta":{},"finish_reason":"length"}]}\n\n'
            b"data: [DONE]\n\n"
        )
        with scripted_http([(200, {}, body)]) as (host, requests):
            gateway = OpenAIGateway(
                api_key="sentinel",
                base_url=host + "/v1",
                recovery_policy=RecoveryPolicy(
                    monotonic=clock,
                    wall=lambda: 0,
                    jitter=lambda ceiling: ceiling / 2,
                    sleeper=virtual_sleep,
                    max_attempts=3,
                ),
            )

            events = [
                event
                async for event in gateway.complete_stream_with_recovery(
                    model="gpt-4o",
                    messages=[LLMMessage(content="prompt")],
                    config=CompletionConfig(temperature=1.0, max_tokens=16384),
                )
            ]

        error = events[-1].error
        assert isinstance(error, RecoveryError)
        assert type(error.inspect_cause()) is LengthTerminationError
        assert error.report.final_failure.inspect_cause() is error.inspect_cause()
        assert error.report.progress.delivered_content == len("sentinel")
        assert error.report.identity == events[0].identity
        assert len(error.report.history) == 1
        assert len(requests) == 1
        assert requests[0][0] == "/v1/chat/completions"
        assert requests[0][1] == (
            b'{"model":"gpt-4o","messages":[{"role":"user","content":"prompt"}],'
            b'"temperature":1.0,"max_tokens":16384,"stream":true,"stream_options":{"include_usage":true}}'
        )
        assert (
            "sentinel" not in str(error) + repr(error) + error.report.model_dump_json()
        )

    @pytest.mark.parametrize("provider,operation,entrypoint", CALLERS)
    def should_preserve_capture_type_original_and_evidence_through_public_callers(
        self, provider, operation, entrypoint, broker_factory
    ):
        original = OSError("sentinel")
        captures, lifecycle, admissions = [], [], []

        def capture(event):
            captures.append(event)
            if event.kind == "body":
                raise original

        async def admission(context):
            admissions.append(context)
            return "allow"

        body = response_body(provider, operation)
        with scripted_http([(200, {}, body)]) as (host, requests):
            gateway = gateway_for(
                provider,
                host,
                RecoveryPolicy(
                    monotonic=clock,
                    wall=lambda: 0,
                    jitter=lambda ceiling: ceiling / 2,
                    sleeper=virtual_sleep,
                    max_attempts=3,
                    wire_observer=capture,
                    observer=lifecycle.append,
                    admission=admission,
                ),
            )
            broker = broker_factory(gateway)
            session = ChatSession(
                broker,
                system_prompt="system",
                config=CONFIG,
                tokenizer_gateway=broker.tokenizer,
            )

            with pytest.raises(RecoveryError) as caught:
                public_request(gateway, operation, entrypoint, broker, session)

        error = caught.value
        cause = error.inspect_cause()
        assert type(cause) is CaptureError
        assert cause.inspect_cause() is original
        assert error.report.final_failure.inspect_cause() is cause
        assert error.report.history == (error.report.final_failure,)
        assert error.report.final_failure.provider == provider
        assert error.report.final_failure.operation == operation
        assert error.report.final_failure.category == "protocol"
        assert not error.report.final_failure.eligible
        assert error.report.progress.observed_content
        assert error.report.progress.delivered_content == 0
        assert error.report.identity.wire_attempt == 1
        assert error.report.identity.attempt_id
        assert admissions == []
        assert len(requests) == 1
        assert requests[0][:2] == expected_request(provider, operation, entrypoint)
        assert (
            next(event for event in captures if event.kind == "request").body
            == requests[0][1]
        )
        assert all(event.identity == error.report.identity for event in captures)
        assert error.inspect_response() == body
        assert [message.content for message in session.messages] == {
            "session": ["system", "prompt"],
            "gateway": ["system"],
            "async": ["system"],
            "broker": ["system"],
        }[entrypoint]
        formatted = (
            "".join(traceback.format_exception(error))
            + "".join(traceback.format_exception(cause))
            + repr(cause)
            + str(cause)
        )
        assert "sentinel" not in formatted + error.report.model_dump_json() + repr(
            lifecycle
        )

    @pytest.mark.parametrize("provider", ["ollama", "omlx", "openai"])
    @pytest.mark.parametrize("entrypoint", ["gateway", "async", "broker", "session"])
    def should_preserve_length_cause_through_stream_consumers(
        self, provider, entrypoint, broker_factory
    ):
        body = response_body(provider, "streaming", "length")
        with scripted_http([(200, {}, body)]) as (host, requests):
            gateway = gateway_for(
                provider,
                host,
                RecoveryPolicy(
                    monotonic=clock,
                    wall=lambda: 0,
                    jitter=lambda ceiling: ceiling / 2,
                    sleeper=virtual_sleep,
                    max_attempts=3,
                    admission=allow,
                ),
            )
            broker = broker_factory(gateway)
            session = ChatSession(
                broker,
                system_prompt="system",
                config=CONFIG,
                tokenizer_gateway=broker.tokenizer,
            )

            with pytest.raises(RecoveryError) as caught:
                public_request(gateway, "streaming", entrypoint, broker, session)

        error = caught.value
        assert type(error.inspect_cause()) is LengthTerminationError
        assert error.report.final_failure.inspect_cause() is error.inspect_cause()
        assert error.report.history == (error.report.final_failure,)
        assert error.report.progress.observed_content
        assert (
            error.report.progress.delivered_content
            == {"ollama": 0, "omlx": 8, "openai": 8}[provider]
        )
        assert not error.report.final_failure.eligible
        assert len(requests) == 1
        assert requests[0][:2] == expected_request(provider, "streaming", entrypoint)
        assert (
            "sentinel"
            not in "".join(traceback.format_exception(error))
            + error.report.model_dump_json()
        )

    @pytest.mark.parametrize("provider,operation", OPERATIONS)
    async def should_retain_prior_failure_and_request_identity_when_capture_stops_a_retry(
        self, provider, operation
    ):
        original = OSError(SECRET)
        captures = []

        def capture(event):
            captures.append(event)
            if event.kind == "body" and event.body != b"busy":
                raise original

        body = response_body(provider, operation)
        with scripted_http([(503, {}, b"busy"), (200, {}, body)]) as (host, requests):
            gateway = gateway_for(
                provider,
                host,
                RecoveryPolicy(
                    monotonic=clock,
                    wall=lambda: 0,
                    jitter=lambda ceiling: ceiling / 2,
                    sleeper=virtual_sleep,
                    max_attempts=3,
                    admission=allow,
                    base_delay=0,
                    wire_observer=capture,
                ),
            )
            with pytest.raises(RecoveryError) as caught:
                await async_request(
                    gateway,
                    operation,
                    {
                        "model": "test",
                        "messages": [LLMMessage(content="prompt")],
                        "config": CONFIG,
                        "object_model": Result if operation == "structured" else None,
                    },
                )

        error = caught.value
        assert type(error.inspect_cause(0)) is httpx.HTTPStatusError
        assert type(error.inspect_cause()) is CaptureError
        assert error.inspect_cause().inspect_cause() is original
        assert error.report.history[0].inspect_cause() is error.inspect_cause(0)
        assert error.report.history[1].inspect_cause() is error.inspect_cause()
        assert (
            error.report.history[0].identity.logical_request_id
            == error.report.identity.logical_request_id
        )
        assert (
            error.report.history[0].identity.attempt_id
            != error.report.identity.attempt_id
        )
        assert error.report.identity.wire_attempt == 2
        assert [request[:2] for request in requests] == [
            expected_request(provider, operation, "async")
        ] * 2
        assert [event.body for event in captures if event.kind == "request"] == [
            request[1] for request in requests
        ]

    @pytest.mark.parametrize("provider", PROVIDERS)
    @pytest.mark.parametrize("stage,count", [("request", 0), ("headers", 1)])
    async def should_stop_capture_before_semantics_without_inventing_attempts(
        self, provider, stage, count
    ):
        original = OSError(SECRET)

        def capture(event):
            if event.kind == stage:
                raise original

        with scripted_http([(503, {}, b"busy")]) as (host, requests):
            gateway = gateway_for(
                provider,
                host,
                RecoveryPolicy(
                    monotonic=clock,
                    wall=lambda: 0,
                    jitter=lambda ceiling: ceiling / 2,
                    sleeper=virtual_sleep,
                    max_attempts=3,
                    admission=allow,
                    wire_observer=capture,
                ),
            )
            with pytest.raises(RecoveryError) as caught:
                await gateway.complete_with_recovery(
                    model="test", messages=[LLMMessage(content="prompt")], config=CONFIG
                )

        error = caught.value
        assert type(error.inspect_cause()) is CaptureError
        assert error.inspect_cause().inspect_cause() is original
        assert error.report.identity.wire_attempt == count
        assert len(error.report.history) == count
        assert len(requests) == count
        assert not error.report.progress.semantic
        assert not error.report.final_failure.eligible

    @pytest.mark.parametrize("entrypoint", ["gateway", "async", "broker"])
    def should_retain_typed_length_for_openai_structured_completion(
        self, entrypoint, broker_factory
    ):
        body = completion('{"answer":"sentinel"}')
        with scripted_http([(200, {}, body)]) as (host, requests):
            gateway = gateway_for(
                "openai",
                host,
                RecoveryPolicy(
                    monotonic=clock,
                    wall=lambda: 0,
                    jitter=lambda ceiling: ceiling / 2,
                    sleeper=virtual_sleep,
                    max_attempts=3,
                ),
            )
            broker = broker_factory(gateway)
            with pytest.raises(RecoveryError) as caught:
                public_request(gateway, "structured", entrypoint, broker, None)

        assert type(caught.value.inspect_cause()) is LengthTerminationError
        assert caught.value.inspect_response() == body
        assert len(requests) == 1
        assert requests[0][:2] == expected_request("openai", "structured", entrypoint)

    @pytest.mark.parametrize("provider", ["ollama", "omlx", "openai"])
    async def should_preserve_successful_ordinary_length_metadata(self, provider):
        body = {
            "ollama": response_body("ollama", "ordinary", "length"),
            "omlx": completion("sentinel"),
            "openai": completion("sentinel"),
        }[provider]
        with scripted_http([(200, {}, body)]) as (host, requests):
            gateway = gateway_for(
                provider,
                host,
                RecoveryPolicy(
                    monotonic=clock,
                    wall=lambda: 0,
                    jitter=lambda ceiling: ceiling / 2,
                    sleeper=virtual_sleep,
                    max_attempts=3,
                ),
            )

            result = await gateway.complete_with_recovery(
                model="test", messages=[LLMMessage(content="prompt")], config=CONFIG
            )

        assert result.finish_reason == "length"
        assert result.content == SECRET
        assert len(requests) == 1

    @pytest.mark.parametrize("provider,operation", OPERATIONS)
    async def should_reject_missing_policy_with_the_same_type_before_dispatch(
        self, provider, operation
    ):
        with scripted_http([]) as (host, requests):
            gateway = gateway_for(provider, host, None)
            with pytest.raises(RecoveryPolicyError):
                await async_request(
                    gateway,
                    operation,
                    {"model": "test", "messages": [LLMMessage(content="prompt")]},
                )

        assert requests == []

    @pytest.mark.parametrize("provider", PROVIDERS)
    @pytest.mark.parametrize(
        "invalid", [{"max_attempts": 0}, {"admission": "sentinel"}, {"sentinel": True}]
    )
    def should_validate_policy_at_gateway_construction_without_disclosing_input(
        self, provider, invalid
    ):
        with pytest.raises(RecoveryPolicyError) as caught:
            gateway_for(provider, "http://127.0.0.1:1", invalid)

        assert "sentinel" not in "".join(traceback.format_exception(caught.value))

    @pytest.mark.parametrize(
        "construct",
        [
            lambda: RecoveryPolicy(
                monotonic=clock,
                wall=lambda: 0,
                jitter=lambda ceiling: ceiling / 2,
                sleeper=virtual_sleep,
                max_attempts=SECRET,
            ),
            lambda: RecoveryPolicy.model_validate({"max_attempts": SECRET}),
            lambda: RecoveryPolicy.model_validate_json(
                json.dumps({"max_attempts": SECRET})
            ),
            lambda: RecoveryPolicy.model_validate_json(SECRET),
            lambda: RecoveryPolicy.model_validate_strings({"max_attempts": SECRET}),
        ],
    )
    def should_use_one_safe_policy_error_across_validation_entrypoints(self, construct):
        with pytest.raises(RecoveryPolicyError) as caught:
            construct()

        assert "sentinel" not in "".join(traceback.format_exception(caught.value))
