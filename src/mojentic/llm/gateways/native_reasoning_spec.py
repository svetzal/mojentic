"""Native reasoning contract v1 through public HTTP and broker continuation."""

import json
from pathlib import Path

import httpx
import pytest
from ollama import ResponseError
from pydantic import BaseModel, ValidationError

from mojentic.llm.completion_config import CompletionConfig
from mojentic.llm.gateways.models import LLMMessage, LLMToolCall, MessageRole
from mojentic.llm.gateways.ollama import OllamaGateway
from mojentic.llm.gateways.ollama_recovery_spec import scripted_http
from mojentic.llm.gateways.omlx import OMLXGateway, OMLXTransport
from mojentic.llm.gateways.omlx_protocol import omlx_settings
from mojentic.llm.gateways.omlx_spec import FIXTURES, ResolveDate
from mojentic.llm.gateways.openai import OpenAIGateway
from mojentic.llm.llm_broker import LLMBroker
from mojentic.llm.reasoning import ReasoningEffort, ReasoningProfile
from mojentic.llm.recovery import RecoveryError, RecoveryPolicy
from mojentic.llm.tools.llm_tool import LLMTool
from scripts.inprocess_http import InProcessTokenizer, clock, virtual_sleep


class DescribeNativeReasoning:
    def should_retain_native_history_separately_through_tool_continuation(self):
        requests = []
        replies = iter(["chat_tool_call.json", "chat_after_tool_result.json"])

        def respond(request):
            requests.append(json.loads(request.content))
            return httpx.Response(
                200, json=json.loads((FIXTURES / next(replies)).read_text())
            )

        gateway = OMLXGateway(
            transport=OMLXTransport(
                omlx_settings(), http_transport=httpx.MockTransport(respond)
            )
        )
        messages = [LLMMessage(content="Resolve tomorrow")]
        config = CompletionConfig(reasoning_effort="low", retain_reasoning=True)

        result = LLMBroker(
            tokenizer=InProcessTokenizer(), model="arbitrary-alias", gateway=gateway
        ).generate(messages, tools=[ResolveDate()], config=config)

        first = json.loads((FIXTURES / "chat_tool_call.json").read_text())["choices"][
            0
        ]["message"]
        assistant = requests[1]["messages"][1]
        assert assistant["reasoning_content"] == first["reasoning_content"]
        assert assistant.get("content") == first.get("content", "")
        assert assistant["tool_calls"] == first["tool_calls"]
        assert (
            requests[1]["messages"][2]["tool_call_id"] == first["tool_calls"][0]["id"]
        )
        assert requests[0]["chat_template_kwargs"] == {"preserve_thinking": True}
        assert requests[0]["reasoning_effort"] == "low"
        assert (
            result
            == json.loads((FIXTURES / "chat_after_tool_result.json").read_text())[
                "choices"
            ][0]["message"]["content"]
        )


CONTRACT = json.loads(
    (Path(__file__).parent / "fixtures/contracts/native_reasoning_v1.json").read_text()
)


class Answer(BaseModel):
    answer: str


class Count(LLMTool):
    def __init__(self) -> None:
        self.calls: list[int] = []

    def run(self, value: int) -> str:
        self.calls.append(value)
        return CONTRACT["tool_result"]

    @property
    def descriptor(self) -> dict:
        return {
            "type": "function",
            "function": {
                "name": "count",
                "description": "Count",
                "parameters": {
                    "type": "object",
                    "properties": {"value": {"type": "integer"}},
                },
            },
        }


def reply(provider, streaming=False, tool=False, terminal=True, finish=None):
    message = {
        "role": "assistant",
        "content": CONTRACT["visible"] if tool else '{"answer":"answer"}',
    }
    message["thinking" if provider == "ollama" else "reasoning_content"] = CONTRACT[
        "reasoning"
    ]
    if tool:
        call = json.loads(json.dumps(CONTRACT["tool_call"]))
        if provider == "ollama":
            call["function"]["arguments"] = json.loads(call["function"]["arguments"])
        if streaming and provider == "omlx":
            call["index"] = 0
        message["tool_calls"] = [call]
    ending = finish or ("tool_calls" if tool and provider == "omlx" else "stop")
    if provider == "ollama":
        return (
            json.dumps({"message": message, "done": terminal, "done_reason": ending})
            + "\n"
        ).encode()
    choice = {"delta" if streaming else "message": message, "finish_reason": ending}
    payload = json.dumps({"choices": [choice]})
    if streaming:
        return (
            "data: " + payload + "\n\n" + ("data: [DONE]\n\n" if terminal else "")
        ).encode()
    return payload.encode()


def gateway_for(provider, host, recovery=False):
    gateway = OllamaGateway if provider == "ollama" else OMLXGateway
    return gateway(
        host=host,
        recovery_policy=RecoveryPolicy(
            monotonic=clock,
            wall=lambda: 0,
            jitter=lambda ceiling: ceiling / 2,
            sleeper=virtual_sleep,
        )
        if recovery
        else None,
    )


def exercise_gateway(gateway, mode, args):
    if mode == "stream":
        chunks = list(gateway.complete_stream(**args))
        assert (
            "".join(chunk.thinking or "" for chunk in chunks) == CONTRACT["reasoning"]
        )
        assert "".join(chunk.content or "" for chunk in chunks) == '{"answer":"answer"}'
        return
    if mode == "events":
        list(gateway.complete_stream_events(**args))
        return
    if mode in ("structured", "recovery_structured"):
        args = args | {"object_model": Answer}
    response = gateway.complete(**args)
    assert response.thinking == CONTRACT["reasoning"]
    assert response.content == '{"answer":"answer"}'
    if mode in ("structured", "recovery_structured"):
        assert response.object == Answer(answer="answer")


class DescribeNativeReasoningWireContract:
    @pytest.mark.parametrize("provider", ["ollama", "omlx"])
    @pytest.mark.parametrize(
        "mode",
        [
            "ordinary",
            "stream",
            "events",
            "structured",
            "recovery",
            "recovery_structured",
        ],
    )
    @pytest.mark.parametrize("retain", [False, True])
    @pytest.mark.parametrize(
        "case", CONTRACT["controls"], ids=lambda case: str(case["effort"])
    )
    def should_send_exact_controls_without_model_inference(
        self, provider, mode, retain, case
    ):
        config = CompletionConfig(
            reasoning_effort=case["effort"], retain_reasoning=retain
        )
        with scripted_http(
            [(200, {}, reply(provider, streaming=mode in ("stream", "events")))]
        ) as (host, requests):
            gateway = gateway_for(provider, host, recovery=mode.startswith("recovery"))
            args = {
                "model": "Qwen3.8-but-no-inferred-profile",
                "messages": [LLMMessage(content="question")],
                "config": config,
            }

            exercise_gateway(gateway, mode, args)
            body = json.loads(requests[0][1])

        controls = {
            key: body[key]
            for key in ("think", "enable_thinking", "reasoning_effort")
            if key in body
        }
        assert controls == case[provider]
        expected = (
            {"preserve_thinking": True} if retain and provider == "omlx" else None
        )
        assert body.get("chat_template_kwargs") == expected

    @pytest.mark.parametrize("provider", ["ollama", "omlx"])
    @pytest.mark.parametrize("streaming", [False, True])
    @pytest.mark.parametrize("retain", [False, True])
    @pytest.mark.parametrize("recovery", [False, True])
    def should_preserve_distinct_payloads_in_broker_tool_history(
        self, provider, streaming, retain, recovery
    ):
        replies = [
            (200, {}, reply(provider, streaming, tool=True)),
            (200, {}, reply(provider, streaming)),
        ]
        with scripted_http(replies) as (host, requests):
            broker = LLMBroker(
                tokenizer=InProcessTokenizer(),
                model="alias",
                gateway=gateway_for(provider, host, recovery),
            )
            messages = [LLMMessage(content="question")]
            config = CompletionConfig(
                retain_reasoning=retain, reasoning_profile=ReasoningProfile.qwen3_8()
            )

            operation = broker.generate_stream if streaming else broker.generate
            result = "".join(operation(messages, tools=[Count()], config=config))
            body = json.loads(requests[1][1])

        native_field = "thinking" if provider == "ollama" else "reasoning_content"
        assistant = body["messages"][1]
        assert assistant.get(native_field) == (
            CONTRACT["reasoning"] if retain else None
        )
        assert assistant["content"] == CONTRACT["visible"]
        arguments = assistant["tool_calls"][0]["function"]["arguments"]
        assert (arguments if provider == "ollama" else json.loads(arguments)) == {
            "value": 7
        }
        assert (
            assistant["tool_calls"][0]["function"]["name"]
            == CONTRACT["tool_call"]["function"]["name"]
        )
        assert body["messages"][2]["content"] == json.dumps(CONTRACT["tool_result"])
        assert result == CONTRACT["visible"] * streaming + '{"answer":"answer"}'
        expected_id = CONTRACT["tool_call"]["id"] if provider == "omlx" else None
        assert body["messages"][2].get("tool_call_id") == expected_id
        call_id = assistant["tool_calls"][0].get("id") if provider == "omlx" else None
        assert call_id == expected_id
        expected_template = (
            {"preserve_thinking": True} if retain and provider == "omlx" else None
        )
        assert body.get("chat_template_kwargs") == expected_template

    @pytest.mark.parametrize("provider", ["ollama", "omlx"])
    @pytest.mark.parametrize(
        "finish,terminal", [("length", True), ("tool_calls", False)]
    )
    def should_not_retain_unfinished_stream_history(self, provider, finish, terminal):
        with scripted_http(
            [
                (200, {}, reply(provider, True, True, terminal, finish)),
                (200, {}, reply(provider, True)),
            ]
        ) as (host, _requests):
            messages = [LLMMessage(content="question")]
            broker = LLMBroker(
                tokenizer=InProcessTokenizer(),
                model="alias",
                gateway=gateway_for(provider, host),
            )

            list(
                broker.generate_stream(
                    messages,
                    tools=[Count()],
                    config=CompletionConfig(retain_reasoning=True),
                )
            )

        assert all(message.thinking is None for message in messages)

    @pytest.mark.parametrize("provider", ["ollama", "omlx"])
    def should_not_fabricate_history_on_stream_failure_or_close(self, provider):
        with scripted_http([(500, {}, b'{"error":"failed"}')]) as (host, _requests):
            messages = [LLMMessage(content="question")]
            stream = LLMBroker(
                tokenizer=InProcessTokenizer(),
                model="alias",
                gateway=gateway_for(provider, host),
            ).generate_stream(
                messages,
                tools=[Count()],
                config=CompletionConfig(retain_reasoning=True),
            )

            with pytest.raises((httpx.HTTPStatusError, ResponseError)):
                list(stream)

        assert messages == [LLMMessage(content="question")]

    @pytest.mark.parametrize("effort", [None, "disabled", "low", "medium", "xhigh"])
    def should_accept_exact_qwen_profile_controls(self, effort):
        assert (
            CompletionConfig(
                reasoning_profile=ReasoningProfile.qwen3_8(), reasoning_effort=effort
            ).reasoning_effort
            == effort
        )

    @pytest.mark.parametrize("effort", ["enabled", "high"])
    def should_reject_unsupported_qwen_controls(self, effort):
        with pytest.raises(ValidationError, match="unsupported by profile qwen3.8"):
            CompletionConfig(
                reasoning_profile=ReasoningProfile.qwen3_8(), reasoning_effort=effort
            )

    def should_reject_history_for_a_profile_without_history(self):
        profile = ReasoningProfile(
            name="boolean",
            supported_efforts=(ReasoningEffort.Enabled,),
            supports_reasoning_history=False,
        )
        with pytest.raises(
            ValidationError, match="does not support native reasoning history"
        ):
            CompletionConfig(reasoning_profile=profile, retain_reasoning=True)

    @pytest.mark.parametrize(
        "config",
        [
            CompletionConfig(reasoning_effort="disabled"),
            CompletionConfig(reasoning_effort="enabled"),
            CompletionConfig(reasoning_effort="xhigh"),
            CompletionConfig(retain_reasoning=True),
            CompletionConfig(reasoning_profile=ReasoningProfile.qwen3_8()),
        ],
    )
    @pytest.mark.parametrize("mode", ["ordinary", "stream", "events", "recovery"])
    def should_reject_new_openai_controls_before_http(self, config, mode):
        gateway = OpenAIGateway(
            api_key="unused",
            recovery_policy=RecoveryPolicy(
                monotonic=clock,
                wall=lambda: 0,
                jitter=lambda ceiling: ceiling / 2,
                sleeper=virtual_sleep,
            )
            if mode == "recovery"
            else None,
        )
        args = {
            "model": "gpt-4o",
            "messages": [LLMMessage(content="question")],
            "config": config,
        }

        with pytest.raises((ValueError, RecoveryError), match="native reasoning"):
            exercise_gateway(gateway, mode, args)

    @pytest.mark.parametrize("provider", ["ollama", "omlx"])
    def should_discard_partial_native_history_when_caller_closes(self, provider):
        with scripted_http([(200, {}, reply(provider, True, True))]) as (
            host,
            _requests,
        ):
            messages = [LLMMessage(content="question")]
            stream = LLMBroker(
                tokenizer=InProcessTokenizer(),
                model="alias",
                gateway=gateway_for(provider, host),
            ).generate_stream(
                messages,
                tools=[Count()],
                config=CompletionConfig(retain_reasoning=True),
            )

            assert next(stream) == CONTRACT["visible"]
            stream.close()

        assert messages == [LLMMessage(content="question")]

    def should_reject_incomplete_ordinary_ollama_history(self):
        with scripted_http([(200, {}, reply("ollama", tool=True, terminal=False))]) as (
            host,
            _requests,
        ):
            messages = [LLMMessage(content="question")]
            broker = LLMBroker(
                tokenizer=InProcessTokenizer(),
                model="alias",
                gateway=gateway_for("ollama", host),
            )

            with pytest.raises(ValueError, match="incomplete Ollama response"):
                broker.generate(
                    messages,
                    tools=[Count()],
                    config=CompletionConfig(retain_reasoning=True),
                )

        assert messages == [LLMMessage(content="question")]

    def should_reject_incomplete_recovery_ollama_history(self):
        tool = Count()
        messages = [LLMMessage(content="question")]
        original = [message.model_copy(deep=True) for message in messages]
        with scripted_http(
            [
                (200, {}, reply("ollama", tool=True, terminal=False)),
                (200, {}, reply("ollama")),
            ]
        ) as (host, requests):
            broker = LLMBroker(
                tokenizer=InProcessTokenizer(),
                model="alias",
                gateway=gateway_for("ollama", host, recovery=True),
            )

            with pytest.raises(RecoveryError) as caught:
                broker.generate(
                    messages,
                    tools=[tool],
                    config=CompletionConfig(retain_reasoning=True),
                )

        assert isinstance(caught.value.inspect_cause(), ValueError)
        assert str(caught.value.inspect_cause()) == "incomplete Ollama response"
        assert caught.value.report.history[-1].category == "protocol"
        assert caught.value.report.history[-1].reason == "semantic_output"
        assert messages == original
        assert tool.calls == []
        bodies = [json.loads(request[1]) for request in requests]
        assert [request[0] for request in requests] == ["/api/chat"]
        assert [body["messages"] for body in bodies] == [
            [{"role": "user", "content": "question"}]
        ]
        assert bodies[0]["stream"] is False
        assert bodies[0]["tools"][0]["function"]["name"] == "count"

    def should_retain_completed_recovery_ollama_history_and_execute_tool_once(self):
        tool = Count()
        messages = [LLMMessage(content="question")]
        with scripted_http(
            [
                (200, {}, reply("ollama", tool=True)),
                (200, {}, reply("ollama")),
            ]
        ) as (host, requests):
            broker = LLMBroker(
                tokenizer=InProcessTokenizer(),
                model="alias",
                gateway=gateway_for("ollama", host, recovery=True),
            )

            result = broker.generate(
                messages, tools=[tool], config=CompletionConfig(retain_reasoning=True)
            )

        assert result == '{"answer":"answer"}'
        assert tool.calls == [7]
        assert len(requests) == 2
        continuation = json.loads(requests[1][1])["messages"]
        assert continuation[1]["thinking"] == CONTRACT["reasoning"]
        assert continuation[1]["content"] == CONTRACT["visible"]
        assert continuation[1]["tool_calls"][0]["function"] == {
            "name": "count",
            "arguments": {"value": 7},
        }
        assert continuation[2]["content"] == json.dumps(CONTRACT["tool_result"])
        assert messages[1].thinking == CONTRACT["reasoning"]

    @pytest.mark.parametrize("provider", ["ollama", "omlx"])
    def should_exclude_capped_ordinary_reasoning_from_history(self, provider):
        with scripted_http(
            [
                (200, {}, reply(provider, tool=True, finish="length")),
                (200, {}, reply(provider)),
            ]
        ) as (host, _requests):
            messages = [LLMMessage(content="question")]
            broker = LLMBroker(
                tokenizer=InProcessTokenizer(),
                model="alias",
                gateway=gateway_for(provider, host),
            )

            broker.generate(
                messages,
                tools=[Count()],
                config=CompletionConfig(retain_reasoning=True),
            )

        assert messages[1].thinking is None

    @pytest.mark.parametrize("mode", ["ordinary", "stream", "events"])
    def should_reject_native_history_on_openai(self, mode):
        gateway = OpenAIGateway(api_key="unused")
        args = {
            "model": "gpt-4o",
            "messages": [
                LLMMessage(
                    role=MessageRole.Assistant, content="visible", thinking="native"
                )
            ],
            "config": CompletionConfig(),
        }
        invoke = {
            "ordinary": lambda: gateway.complete(**args),
            "stream": lambda: list(gateway.complete_stream(**args)),
            "events": lambda: list(gateway.complete_stream_events(**args)),
        }

        with pytest.raises(ValueError, match="native reasoning history"):
            invoke[mode]()

    @pytest.mark.parametrize("provider", ["ollama", "omlx"])
    def should_preserve_ordered_multiple_native_tool_calls(self, provider):
        calls = [
            LLMToolCall(
                id="first", name="count", arguments={"value": 7, "nested": {"ok": True}}
            ),
            LLMToolCall(
                id="second", name="count", arguments={"value": 8, "items": [1, None]}
            ),
        ]
        messages = [
            LLMMessage(
                role=MessageRole.Assistant,
                content=CONTRACT["visible"],
                thinking=CONTRACT["reasoning"],
                tool_calls=calls,
            )
        ]
        with scripted_http([(200, {}, reply(provider))]) as (host, requests):
            gateway_for(provider, host).complete(
                model="alias", messages=messages, config=CompletionConfig()
            )
            assistant = json.loads(requests[0][1])["messages"][0]

        expected_ids = {"omlx": ["first", "second"], "ollama": [None, None]}
        assert [call.get("id") for call in assistant["tool_calls"]] == expected_ids[
            provider
        ]
        arguments = [call["function"]["arguments"] for call in assistant["tool_calls"]]
        parsed = (
            arguments
            if provider == "ollama"
            else [json.loads(value) for value in arguments]
        )
        assert parsed == [call.arguments for call in calls]
        assert assistant["content"] == CONTRACT["visible"]
        assert (
            assistant["thinking" if provider == "ollama" else "reasoning_content"]
            == CONTRACT["reasoning"]
        )

    def should_discard_reasoning_after_provider_error_frame(self):
        body = (
            reply("omlx", True, True, terminal=False)
            + b'data: {"error":{"message":"failed"}}\n\ndata: [DONE]\n\n'
        )
        with scripted_http([(200, {}, body)]) as (host, _requests):
            messages = [LLMMessage(content="question")]
            broker = LLMBroker(
                tokenizer=InProcessTokenizer(),
                model="alias",
                gateway=gateway_for("omlx", host),
            )

            with pytest.raises(ValueError, match="stream failed"):
                list(
                    broker.generate_stream(
                        messages,
                        tools=[Count()],
                        config=CompletionConfig(retain_reasoning=True),
                    )
                )

        assert messages == [LLMMessage(content="question")]

    def should_reject_named_effort_for_boolean_only_profile(self):
        profile = ReasoningProfile(
            name="boolean",
            supported_efforts=(ReasoningEffort.Disabled, ReasoningEffort.Enabled),
            supports_reasoning_history=False,
        )

        with pytest.raises(ValidationError, match="unsupported by profile boolean"):
            CompletionConfig(reasoning_profile=profile, reasoning_effort="low")
