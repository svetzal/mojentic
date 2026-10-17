"""anthropic-structured-v1: gateway provider and broker consumer HTTP contract."""

import asyncio
import json
from collections.abc import Callable

import pytest
from pydantic import BaseModel, Field, ValidationError

from mojentic.llm.completion_config import CompletionConfig
from mojentic.llm.gateways.anthropic import AnthropicGateway
from mojentic.llm.gateways.cloud_recovery_spec import success
from mojentic.llm.gateways.models import LLMMessage, MessageRole
from mojentic.llm.gateways.ollama_recovery_spec import scripted_http
from mojentic.llm.gateways.omlx_recovery_spec import (
    broker_factory as shared_broker_factory,
)
from mojentic.llm.llm_broker import LLMBroker
from mojentic.llm.recovery import (
    CaptureError,
    LengthTerminationError,
    RecoveryError,
    RecoveryPolicy,
)

broker_factory = shared_broker_factory


class Answer(BaseModel):
    answer: str


class ScoredAnswer(BaseModel):
    answer: str
    score: int | None = Field(default=None, ge=0, le=3)


MESSAGES = [
    LLMMessage(role=MessageRole.System, content="Be precise"),
    LLMMessage(content="héllo 世界"),
    LLMMessage(role=MessageRole.Assistant, content="réponse 🌍"),
    LLMMessage(content="finish"),
]
EXPECTED = {
    "model": "claude-test",
    "system": "Be precise",
    "messages": [
        {"role": "user", "content": "héllo 世界"},
        {"role": "assistant", "content": "réponse 🌍"},
        {"role": "user", "content": "finish"},
    ],
    "temperature": 0.25,
    "max_tokens": 17,
    "output_config": {
        "format": {
            "type": "json_schema",
            "schema": {
                "type": "object",
                "title": "Answer",
                "properties": {"answer": {"type": "string", "title": "Answer"}},
                "additionalProperties": False,
                "required": ["answer"],
            },
        }
    },
}


def structured_response(
    text: str = '{"answer":"done"}', finish: str = "end_turn"
) -> bytes:
    frame = json.loads(success("anthropic"))
    frame["content"][0]["text"] = text
    frame["stop_reason"] = finish
    return json.dumps(frame).encode()


def invoke(
    role: str,
    gateway: AnthropicGateway,
    broker_factory: Callable[[AnthropicGateway], LLMBroker],
    object_model: type[BaseModel] = Answer,
) -> BaseModel:
    config = CompletionConfig(temperature=0.25, max_tokens=17)
    if role == "consumer":
        broker = broker_factory(gateway)
        broker.model = "claude-test"
        return broker.generate_object(MESSAGES, object_model, config=config)
    return asyncio.run(
        gateway.complete_with_recovery(
            model="claude-test",
            messages=MESSAGES,
            object_model=object_model,
            config=config,
        )
    ).object


class DescribeAnthropicStructuredContract:
    async def should_replay_frozen_schema_history_and_controls_at_http_boundary(self):
        captures = []
        lifecycle = []
        policy = RecoveryPolicy(
            max_attempts=2,
            base_delay=0,
            wire_observer=captures.append,
            observer=lifecycle.append,
        )
        with scripted_http([(503, {}, b"busy"), (200, {}, structured_response())]) as (
            host,
            requests,
        ):
            gateway = AnthropicGateway(
                api_key="credential-sentinel", base_url=host, recovery_policy=policy
            )

            response = await gateway.complete_with_recovery(
                model="claude-test",
                messages=MESSAGES,
                object_model=Answer,
                config=CompletionConfig(temperature=0.25, max_tokens=17),
            )

        assert len(requests) == 2
        assert [path for path, _, _ in requests] == ["/v1/messages"] * 2
        assert requests[0][1] == requests[1][1]
        assert (
            requests[0][1]
            == json.dumps(EXPECTED, ensure_ascii=False, separators=(",", ":")).encode()
        )
        assert json.loads(requests[0][1]) == EXPECTED
        sent = [event for event in captures if event.kind == "request"]
        assert [event.body for event in sent] == [requests[0][1]] * 2
        assert len({event.identity.logical_request_id for event in sent}) == 1
        assert len({event.identity.attempt_id for event in sent}) == 2
        assert [event.identity.wire_attempt for event in sent] == [1, 2]
        assert response.object == Answer(answer="done")
        assert response.recovery_report.history[0].eligible
        assert response.metadata["recovery"] == response.recovery_report.model_dump(
            mode="json"
        )
        assert [event.transition for event in lifecycle] == [
            "attempt_started",
            "attempt_failed",
            "delay_scheduled",
            "retry_started",
            "attempt_started",
            "attempt_succeeded",
        ]
        assert (
            response.recovery_report.identity.logical_request_id
            == sent[0].identity.logical_request_id
        )
        assert "credential-sentinel" not in repr(lifecycle)
        assert "réponse" not in repr(lifecycle)

    @pytest.mark.parametrize("role", ["provider", "consumer"])
    def should_verify_identical_recovery_contract_for_gateway_and_broker(
        self, role, broker_factory
    ):
        with scripted_http([(503, {}, b"busy"), (200, {}, structured_response())]) as (
            host,
            requests,
        ):
            gateway = AnthropicGateway(
                api_key="test",
                base_url=host,
                recovery_policy=RecoveryPolicy(max_attempts=2, base_delay=0),
            )

            result = invoke(role, gateway, broker_factory)

        assert result == Answer(answer="done")
        assert len(requests) == 2
        assert requests[0][1] == requests[1][1]
        assert json.loads(requests[0][1]) == EXPECTED

    @pytest.mark.parametrize("role", ["provider", "consumer"])
    @pytest.mark.parametrize(
        "text,finish,cause",
        [
            ("not-json", "end_turn", ValidationError),
            ('{"answer":3}', "end_turn", ValidationError),
            ('{"answer":"truncated', "max_tokens", LengthTerminationError),
            ('{"answer":"complete"}', "max_tokens", LengthTerminationError),
        ],
    )
    def should_preserve_typed_decode_failures_without_replay(
        self, role, text, finish, cause, broker_factory
    ):
        lifecycle = []
        with scripted_http([(200, {}, structured_response(text, finish))]) as (
            host,
            requests,
        ):
            gateway = AnthropicGateway(
                api_key="test",
                base_url=host,
                recovery_policy=RecoveryPolicy(
                    max_attempts=3, observer=lifecycle.append
                ),
            )

            with pytest.raises(RecoveryError) as caught:
                invoke(role, gateway, broker_factory)

        assert len(requests) == 1
        assert json.loads(requests[0][1]) == EXPECTED
        assert isinstance(caught.value.inspect_cause(), cause)
        assert caught.value.report.final_failure.operation == "structured"
        assert caught.value.report.final_failure.provider == "anthropic"
        assert not caught.value.report.final_failure.eligible
        assert caught.value.report.progress.observed_content
        assert caught.value.report.progress.delivered_content == 0
        assert text not in str(caught.value)
        assert text not in repr(lifecycle)

    @pytest.mark.parametrize("role", ["provider", "consumer"])
    @pytest.mark.parametrize(
        "status,attempts,count", [(503, None, 1), (503, 2, 2), (401, 3, 1), (400, 3, 1)]
    )
    def should_bound_attempts_and_refuse_permanent_errors(
        self, role, status, attempts, count, broker_factory
    ):
        with scripted_http([(status, {}, b"private")] * count) as (host, requests):
            gateway = AnthropicGateway(
                api_key="test",
                base_url=host,
                recovery_policy=RecoveryPolicy(
                    base_delay=0, **({"max_attempts": attempts} if attempts else {})
                ),
            )

            with pytest.raises(RecoveryError) as caught:
                invoke(role, gateway, broker_factory)

        assert len(requests) == count
        assert all(json.loads(body) == EXPECTED for _, body, _ in requests)
        assert len(caught.value.report.history) == count
        assert caught.value.report.final_failure.http_status == status

    @pytest.mark.parametrize("role", ["provider", "consumer"])
    def should_stop_on_capture_failure_with_original_cause(self, role, broker_factory):
        original = OSError("capture-secret")

        def capture(event):
            if event.kind == "body":
                raise original

        with scripted_http([(200, {}, structured_response())]) as (host, requests):
            gateway = AnthropicGateway(
                api_key="test",
                base_url=host,
                recovery_policy=RecoveryPolicy(max_attempts=3, wire_observer=capture),
            )

            with pytest.raises(RecoveryError) as caught:
                invoke(role, gateway, broker_factory)

        assert len(requests) == 1
        assert isinstance(caught.value.inspect_cause(), CaptureError)
        assert caught.value.inspect_cause().inspect_cause() is original
        assert caught.value.report.progress.observed_content
        assert not caught.value.report.final_failure.eligible
        assert "capture-secret" not in str(caught.value)

    @pytest.mark.parametrize("role", ["provider", "consumer"])
    @pytest.mark.parametrize(
        "text,expected",
        [
            ('{"answer":"ok"}', {"answer": "ok", "score": None}),
            ('{"answer":"ok","score":2}', {"answer": "ok", "score": 2}),
        ],
    )
    def should_validate_optional_fields_with_original_pydantic_model(
        self, role, text, expected, broker_factory
    ):
        with scripted_http([(200, {}, structured_response(text))]) as (host, requests):
            gateway = AnthropicGateway(
                api_key="test", base_url=host, recovery_policy=RecoveryPolicy()
            )

            result = invoke(role, gateway, broker_factory, ScoredAnswer)

        assert result == ScoredAnswer(**expected)
        assert len(requests) == 1
        schema = json.loads(requests[0][1])["output_config"]["format"]["schema"]
        assert schema["additionalProperties"] is False

    @pytest.mark.parametrize("role", ["provider", "consumer"])
    def should_validate_constraints_removed_from_provider_schema(
        self, role, broker_factory
    ):
        with scripted_http(
            [(200, {}, structured_response('{"answer":"ok","score":4}'))]
        ) as (host, requests):
            gateway = AnthropicGateway(
                api_key="test",
                base_url=host,
                recovery_policy=RecoveryPolicy(max_attempts=3),
            )

            with pytest.raises(RecoveryError) as caught:
                invoke(role, gateway, broker_factory, ScoredAnswer)

        assert len(requests) == 1
        assert isinstance(caught.value.inspect_cause(), ValidationError)
        schema = json.loads(requests[0][1])["output_config"]["format"]["schema"]
        assert "maximum" not in schema["properties"]["score"]["anyOf"][0]

    @pytest.mark.parametrize("decision", ["reject", None])
    async def should_require_explicit_admission_decision_when_hook_is_present(
        self, decision
    ):
        async def admission(context):
            return decision

        with scripted_http([(503, {}, b"busy")]) as (host, requests):
            gateway = AnthropicGateway(
                api_key="test",
                base_url=host,
                recovery_policy=RecoveryPolicy(
                    max_attempts=3,
                    base_delay=0,
                    admission=admission,
                ),
            )

            with pytest.raises(RecoveryError):
                await gateway.complete_with_recovery(
                    model="claude-test", messages=MESSAGES, object_model=Answer
                )

        assert len(requests) == 1

    async def should_freeze_schema_and_history_before_admission_mutates_inputs(self):
        class Answer(BaseModel):
            answer: str

        messages = [message.model_copy(deep=True) for message in MESSAGES]
        config = CompletionConfig(temperature=0.25, max_tokens=17)

        async def admission(context):
            messages[1].content = "changed"
            config.temperature = 0.9
            Answer.model_fields["answer"].title = "Changed schema"
            Answer.model_rebuild(force=True)
            return "allow"

        with scripted_http([(503, {}, b"busy"), (200, {}, structured_response())]) as (
            host,
            requests,
        ):
            gateway = AnthropicGateway(
                api_key="test",
                base_url=host,
                recovery_policy=RecoveryPolicy(
                    max_attempts=2, base_delay=0, admission=admission
                ),
            )

            response = await gateway.complete_with_recovery(
                model="claude-test",
                messages=messages,
                object_model=Answer,
                config=config,
            )

        assert response.object == Answer(answer="done")
        assert len(requests) == 2
        assert requests[0][1] == requests[1][1]
        assert json.loads(requests[1][1]) == EXPECTED
