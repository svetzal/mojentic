"""Request fidelity v1 exercised through captured in-process HTTP requests."""

import asyncio
import json
from pathlib import Path

import pytest
from pydantic import BaseModel

from mojentic.llm.chat_session import ChatSession
from mojentic.llm.completion_config import CompletionConfig
from mojentic.llm.gateways.anthropic import AnthropicGateway
from mojentic.llm.gateways.models import LLMMessage, MessageRole
from mojentic.llm.gateways.ollama import OllamaGateway
from mojentic.llm.gateways.ollama_recovery_spec import scripted_http
from mojentic.llm.gateways.omlx import OMLXGateway
from mojentic.llm.gateways.omlx_recovery_spec import allow
from mojentic.llm.gateways.openai import OpenAIGateway
from mojentic.llm.gateways.openai_model_registry import (
    ModelCapabilities,
    ModelType,
    OpenAIModelRegistry,
)
from mojentic.llm.gateways.stream_events import StreamCompleted, StreamContent
from mojentic.llm.llm_broker import LLMBroker
from mojentic.llm.recovery import RecoveryPolicy
from mojentic.llm.tools.llm_tool import LLMTool
from mojentic.tracer import TracerSystem
from scripts.inprocess_http import InProcessTokenizer, clock, virtual_sleep

CONTRACT = json.loads(
    (Path(__file__).parent / "fixtures/contracts/request_fidelity_v1.json").read_text()
)


class DescribeRequestFidelity:
    def should_omit_unset_session_controls_at_http_boundary(self):
        frame = json.loads(CONTRACT["responses"]["ollama-complete"])
        frame["message"]["role"] = "assistant"
        reply = json.dumps(frame).encode()
        with scripted_http([(200, {}, reply)]) as (host, requests):
            broker = LLMBroker(
                tokenizer=InProcessTokenizer(),
                model="test",
                gateway=OllamaGateway(
                    host=host,
                    recovery_policy=RecoveryPolicy(
                        monotonic=clock,
                        wall=lambda: 0,
                        jitter=lambda ceiling: ceiling / 2,
                        sleeper=virtual_sleep,
                    ),
                ),
                tracer=TracerSystem(),
            )
            session = ChatSession(broker, max_context=8192)

            assert session.send("hello") == "answer"

        assert json.loads(requests[0][1])["options"] == {}
        assert session.max_context == 8192


# The shared semantic response omits envelopes required by Python's strict
# recovery decoders. Add provider envelope fields without changing its content.
def reply(provider: str, operation: str) -> bytes:
    protocol = "ollama" if provider == "ollama" else "openai"
    raw = CONTRACT["responses"][f"{protocol}-{operation}"]
    if protocol == "ollama":
        frames = [json.loads(line) for line in raw.splitlines()]
        for frame in frames:
            frame["message"]["role"] = "assistant"
        return ("\n".join(json.dumps(frame) for frame in frames) + "\n").encode()
    return raw.encode()


def gateway_for(provider: str, host: str, recovery: bool = False):
    policy = (
        RecoveryPolicy(
            monotonic=clock,
            wall=lambda: 0,
            jitter=lambda ceiling: ceiling / 2,
            sleeper=virtual_sleep,
            max_attempts=2,
            base_delay=0,
            admission=allow,
        )
        if recovery
        else None
    )
    if provider == "ollama":
        return OllamaGateway(host=host, recovery_policy=policy)
    if provider == "omlx":
        return OMLXGateway(host=host, recovery_policy=policy)
    return OpenAIGateway(
        api_key="loopback", base_url=host + "/v1", recovery_policy=policy
    )


def assert_controls(payload: dict, provider: str, controls: dict) -> None:
    mapping = {
        "temperature": "temperature",
        "max_tokens": "max_tokens",
        "top_p": "top_p",
    }
    if provider == "ollama":
        mapping |= {"num_ctx": "num_ctx", "max_tokens": "num_predict", "top_k": "top_k"}
    if provider == "omlx":
        mapping["top_k"] = "top_k"
    expected = {
        wire: controls[field]
        for field, wire in mapping.items()
        if controls.get(field) is not None
    }
    body = payload.get("options", payload)
    parameter_names = {
        "temperature",
        "max_tokens",
        "max_completion_tokens",
        "num_ctx",
        "num_predict",
        "top_p",
        "top_k",
    }
    assert {
        key: value for key, value in body.items() if key in parameter_names
    } == expected


class Answer(BaseModel):
    answer: str


class DescribeSharedRequestFidelity:
    @pytest.mark.parametrize("case", CONTRACT["cases"], ids=lambda case: case["name"])
    @pytest.mark.parametrize("provider", ["ollama", "openai", "omlx"])
    def should_preserve_controls_through_broker_events(self, case, provider):
        with scripted_http([(200, {}, reply(provider, "events"))]) as (host, requests):
            broker = LLMBroker(
                tokenizer=InProcessTokenizer(),
                model="gpt-4o",
                gateway=gateway_for(provider, host),
                tracer=TracerSystem(),
            )

            events = list(
                broker.generate_stream_events(
                    [LLMMessage(content="hello")],
                    config=CompletionConfig(**case["config"]),
                )
            )

        assert (
            "".join(event.text for event in events if isinstance(event, StreamContent))
            == "answer"
        )
        assert [
            event.type for event in events if not isinstance(event, StreamContent)
        ] == ["completed"]
        assert isinstance(events[-1], StreamCompleted)
        assert events[-1].metadata.finish_reason == "stop"
        assert len(requests) == 1
        assert_controls(json.loads(requests[0][1]), provider, case["config"])

    @pytest.mark.parametrize("case", CONTRACT["cases"], ids=lambda case: case["name"])
    @pytest.mark.parametrize("provider", ["ollama", "openai", "omlx"])
    def should_preserve_controls_and_history_through_session_stream(
        self, case, provider
    ):
        with scripted_http([(200, {}, reply(provider, "legacy"))]) as (host, requests):
            broker = LLMBroker(
                tokenizer=InProcessTokenizer(),
                model="gpt-4o",
                gateway=gateway_for(provider, host),
                tracer=TracerSystem(),
            )
            session = ChatSession(
                broker, config=CompletionConfig(**case["config"]), max_context=4096
            )
            session.insert_message(
                LLMMessage(role=MessageRole.User, content="previous question")
            )
            session.insert_message(
                LLMMessage(role=MessageRole.Assistant, content="previous answer")
            )

            content = "".join(session.send_stream("hello"))

        assert content == "answer"
        assert len(requests) == 1
        payload = json.loads(requests[0][1])
        assert_controls(payload, provider, case["config"])
        expected_history = [
            ("system", session.system_prompt),
            ("user", "previous question"),
            ("assistant", "previous answer"),
            ("user", "hello"),
        ]
        assert [
            (message["role"], message["content"]) for message in payload["messages"]
        ] == expected_history
        assert [
            (message.role.value, message.content) for message in session.messages
        ] == (expected_history + [("assistant", "answer")])
        assert session.max_context == 4096

    @pytest.mark.parametrize("case", CONTRACT["cases"], ids=lambda case: case["name"])
    @pytest.mark.parametrize("provider", ["ollama", "openai", "omlx"])
    @pytest.mark.parametrize("operation", ["complete", "object", "legacy", "events"])
    @pytest.mark.parametrize("recovery", [False, True])
    def should_execute_shared_cases(self, case, provider, operation, recovery):
        success = (
            200,
            {"Content-Type": "application/json"},
            reply(provider, operation),
        )
        replies = scripted_replies(success, recovery)
        with scripted_http(replies) as (host, requests):
            gateway = gateway_for(provider, host, recovery)
            args = {
                "model": "gpt-4o",
                "messages": [LLMMessage(content="hello")],
                "config": CompletionConfig(**case["config"]),
            }

            result = execute(gateway, operation, recovery, args)

        assert result == "answer"
        for _, body, _ in requests:
            assert_controls(json.loads(body), provider, case["config"])
        assert_resends(requests, recovery)

    @pytest.mark.parametrize("case", CONTRACT["cases"], ids=lambda case: case["name"])
    @pytest.mark.parametrize("provider", ["ollama", "openai", "omlx"])
    @pytest.mark.parametrize("route", ["broker", "object", "session", "stream"])
    def should_preserve_controls_through_public_routes(self, case, provider, route):
        operation = {
            "broker": "complete",
            "object": "object",
            "session": "complete",
            "stream": "legacy",
        }[route]
        with scripted_http([(200, {}, reply(provider, operation))]) as (host, requests):
            broker = LLMBroker(
                tokenizer=InProcessTokenizer(),
                model="gpt-4o",
                gateway=gateway_for(provider, host),
                tracer=TracerSystem(),
            )
            config = CompletionConfig(**case["config"])
            messages = [LLMMessage(content="hello")]
            result = public_route(broker, route, config, messages)

        assert result == "answer"
        assert_controls(json.loads(requests[0][1]), provider, case["config"])


def execute(gateway, operation: str, recovery: bool, args: dict) -> str:
    if operation == "object":
        return gateway.complete(**args, object_model=Answer).object.answer
    if operation == "complete":
        return gateway.complete(**args).content
    if operation == "legacy":
        return "".join(chunk.content or "" for chunk in gateway.complete_stream(**args))
    if recovery:
        return asyncio.run(recovery_content(gateway, args))
    events = list(gateway.complete_stream_events(**args))
    assert events[-1].type == "completed"
    return "".join(event.text for event in events if event.type == "content")


async def recovery_content(gateway, args: dict) -> str:
    events = [event async for event in gateway.complete_stream_with_recovery(**args)]
    assert events[-1].kind == "completed"
    return "".join(event.text for event in events if event.kind == "content")


def public_route(
    broker, route: str, config: CompletionConfig, messages: list[LLMMessage]
) -> str:
    if route == "object":
        return broker.generate_object(messages, Answer, config=config).answer
    if route == "stream":
        return "".join(broker.generate_stream(messages, config=config))
    if route == "session":
        return ChatSession(broker, config=config, max_context=8192).send("hello")
    return broker.generate(messages, config=config)


class Count(LLMTool):
    def __init__(self) -> None:
        super().__init__()
        self.calls: list[str] = []

    def run(self, value: str) -> str:
        self.calls.append(value)
        return value

    @property
    def descriptor(self) -> dict:
        return {
            "type": "function",
            "function": {
                "name": "count",
                "description": "Count",
                "parameters": {
                    "type": "object",
                    "properties": {"value": {"type": "string"}},
                    "required": ["value"],
                },
            },
        }


def tool_reply(provider: str) -> bytes:
    call = json.loads(json.dumps(CONTRACT["tool_call"]))
    if provider == "ollama":
        call["function"]["arguments"] = json.loads(call["function"]["arguments"])
        frame = json.loads(reply(provider, "complete"))
        frame["message"] |= {"content": "", "tool_calls": [call]}
    else:
        frame = json.loads(reply(provider, "complete"))
        frame["choices"][0] = {
            "message": {"role": "assistant", "content": "", "tool_calls": [call]},
            "finish_reason": "tool_calls",
        }
    return json.dumps(frame).encode()


class DescribeContinuationFidelity:
    @pytest.mark.parametrize("provider", ["ollama", "openai", "omlx"])
    @pytest.mark.parametrize("case", CONTRACT["cases"], ids=lambda case: case["name"])
    def should_keep_controls_and_tool_history_on_admitted_resend(self, provider, case):
        error = CONTRACT["retryable_error"]
        replies = [
            (200, {}, tool_reply(provider)),
            (error["status"], {}, error["body"].encode()),
            (200, {}, reply(provider, "complete")),
        ]
        tool = Count()
        with scripted_http(replies) as (host, requests):
            broker = LLMBroker(
                tokenizer=InProcessTokenizer(),
                model="gpt-4o",
                gateway=gateway_for(provider, host, True),
                tracer=TracerSystem(),
            )
            result = ChatSession(
                broker, tools=[tool], config=CompletionConfig(**case["config"])
            ).send("hello")

        assert result == "answer"
        assert tool.calls == ["next-π"]
        assert requests[1][1] == requests[2][1]
        for _, body, _ in requests:
            assert_controls(json.loads(body), provider, case["config"])
        history = json.loads(requests[1][1])["messages"]
        assert history[-2]["tool_calls"][0]["function"]["name"] == "count"
        assert json.loads(history[-1]["content"]) == "next-π"


class DescribeMigrationFidelity:
    @pytest.mark.parametrize("provider", ["ollama", "openai", "omlx"])
    @pytest.mark.parametrize(
        "controls",
        [
            {},
            {"temperature": 0},
            {"temperature": 1.0, "num_ctx": 32768, "max_tokens": 16384},
        ],
    )
    def should_forward_only_explicit_deprecated_broker_keywords(
        self, provider, controls
    ):
        with scripted_http([(200, {}, reply(provider, "complete"))]) as (
            host,
            requests,
        ):
            broker = LLMBroker(
                tokenizer=InProcessTokenizer(),
                model="gpt-4o",
                gateway=gateway_for(provider, host),
                tracer=TracerSystem(),
            )
            result = broker.generate([LLMMessage(content="hello")], **controls)

        assert result == "answer"
        assert_controls(json.loads(requests[0][1]), provider, controls)

    @pytest.mark.parametrize("provider", ["ollama", "openai", "omlx"])
    def should_omit_controls_for_gateway_keywords_without_config(self, provider):
        with scripted_http([(200, {}, reply(provider, "complete"))]) as (
            host,
            requests,
        ):
            result = gateway_for(provider, host, True).complete(
                model="gpt-4o", messages=[LLMMessage(content="hello")]
            )

        assert result.content == "answer"
        assert_controls(json.loads(requests[0][1]), provider, {})

    @pytest.mark.parametrize("temperature,expected", [(None, None), (0, 0.7)])
    def should_adapt_only_explicit_temperature_to_registered_fixed_value(
        self, temperature, expected
    ):
        with scripted_http([(200, {}, reply("openai", "complete"))]) as (
            host,
            requests,
        ):
            gateway = gateway_for("openai", host)
            gateway.model_registry = OpenAIModelRegistry()
            gateway.model_registry.register_model(
                "fixed",
                ModelCapabilities(
                    model_type=ModelType.CHAT, supported_temperatures=[0.7]
                ),
            )
            result = gateway.complete(
                model="fixed",
                messages=[LLMMessage(content="hello")],
                config=CompletionConfig(temperature=temperature),
            )

        assert result.content == "answer"
        assert_controls(json.loads(requests[0][1]), "openai", {"temperature": expected})

    def should_warn_and_drop_effort_for_non_reasoning_model(self, caplog):
        with scripted_http([(200, {}, reply("openai", "complete"))]) as (
            host,
            requests,
        ):
            result = gateway_for("openai", host).complete(
                model="gpt-4o",
                messages=[LLMMessage(content="hello")],
                config=CompletionConfig(reasoning_effort="high"),
            )

        assert result.content == "answer"
        assert "reasoning_effort" not in json.loads(requests[0][1])
        assert "does not support reasoning_effort" in caplog.text


def anthropic_reply(operation: str) -> bytes:
    semantic = json.loads(CONTRACT["responses"][f"openai-{operation}"])["choices"][0][
        "message"
    ]["content"]
    return json.dumps(
        {
            "id": "msg",
            "type": "message",
            "role": "assistant",
            "model": "reported",
            "content": [{"type": "text", "text": semantic}],
            "stop_reason": "end_turn",
            "usage": {"input_tokens": 2, "output_tokens": 3},
        }
    ).encode()


class DescribeAnthropicFidelity:
    @pytest.mark.parametrize("case", CONTRACT["cases"], ids=lambda case: case["name"])
    @pytest.mark.parametrize(
        "model,fallback", [("claude-haiku-4-5", 64000), ("unknown", 4096)]
    )
    @pytest.mark.parametrize(
        "route,recovery",
        [
            ("gateway", False),
            ("broker", False),
            ("session", False),
            ("gateway", True),
            ("broker", True),
            ("object", True),
            ("session", True),
        ],
    )
    def should_apply_only_required_fallback_and_explicit_controls(
        self, case, model, fallback, route, recovery
    ):
        operation = "object" if route == "object" else "complete"
        replies = scripted_replies((200, {}, anthropic_reply(operation)), recovery)
        with scripted_http(replies) as (host, requests):
            policy = (
                RecoveryPolicy(
                    monotonic=clock,
                    wall=lambda: 0,
                    jitter=lambda ceiling: ceiling / 2,
                    sleeper=virtual_sleep,
                    max_attempts=2,
                    base_delay=0,
                    admission=allow,
                )
                if recovery
                else None
            )
            gateway = AnthropicGateway(
                api_key="loopback", base_url=host, recovery_policy=policy
            )
            config = CompletionConfig(**case["config"])
            messages = [LLMMessage(content="hello")]
            result = anthropic_route(gateway, route, model, messages, config)

        assert result == "answer"
        expected = {
            key: value
            for key, value in case["config"].items()
            if key in {"temperature", "max_tokens", "top_p", "top_k"}
            and value is not None
        }
        expected.setdefault("max_tokens", fallback)
        for _, body, _ in requests:
            payload = json.loads(body)
            assert {key: payload[key] for key in expected} == expected
            assert set(payload) & {
                "temperature",
                "max_tokens",
                "top_p",
                "top_k",
                "num_ctx",
                "num_predict",
            } == set(expected)
        assert_resends(requests, recovery)


def anthropic_route(
    gateway,
    route: str,
    model: str,
    messages: list[LLMMessage],
    config: CompletionConfig,
) -> str:
    if route == "gateway":
        return gateway.complete(model=model, messages=messages, config=config).content
    broker = LLMBroker(
        tokenizer=InProcessTokenizer(),
        model=model,
        gateway=gateway,
        tracer=TracerSystem(),
    )
    return public_route(broker, route, config, messages)


def scripted_replies(success: tuple, recovery: bool) -> list[tuple]:
    error = CONTRACT["retryable_error"]
    return ([(error["status"], {}, error["body"].encode())] if recovery else []) + [
        success
    ]


def assert_resends(requests: list, recovery: bool) -> None:
    if recovery:
        assert requests[0][1] == requests[1][1]


class DescribeAnthropicMigration:
    @pytest.mark.parametrize("max_tokens", [2000, 16384])
    @pytest.mark.parametrize("recovery", [False, True])
    def should_reproduce_supported_former_sdk_and_config_limits(
        self, max_tokens, recovery
    ):
        with scripted_http(
            scripted_replies((200, {}, anthropic_reply("complete")), recovery)
        ) as (host, requests):
            gateway = AnthropicGateway(
                api_key="loopback",
                base_url=host,
                recovery_policy=RecoveryPolicy(
                    monotonic=clock,
                    wall=lambda: 0,
                    jitter=lambda ceiling: ceiling / 2,
                    sleeper=virtual_sleep,
                    max_attempts=2,
                    base_delay=0,
                    admission=allow,
                )
                if recovery
                else None,
            )
            result = gateway.complete(
                model="unknown",
                messages=[LLMMessage(content="hello")],
                config=CompletionConfig(temperature=1.0, max_tokens=max_tokens),
            )

        assert result.content == "answer"
        assert json.loads(requests[-1][1])["temperature"] == 1.0
        assert json.loads(requests[-1][1])["max_tokens"] == max_tokens
        assert_resends(requests, recovery)
