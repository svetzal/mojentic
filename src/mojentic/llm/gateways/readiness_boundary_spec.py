"""October 12 public-boundary evidence using existing controlled HTTP fixtures."""

import json
from contextlib import nullcontext

import pytest

from mojentic.llm.chat_session import ChatSession
from mojentic.llm.gateways.models import LLMMessage
from mojentic.llm.gateways.ollama_recovery_spec import scripted_http
from mojentic.llm.gateways.omlx_recovery_spec import allow
from mojentic.llm.gateways.typed_errors_spec import (
    CONFIG,
    expected_request,
    gateway_for,
    response_body,
)
from mojentic.llm.llm_broker import LLMBroker
from mojentic.llm.recovery import RecoveryError, RecoveryPolicy


def outcome_context(eligible: bool):
    return nullcontext() if eligible else pytest.raises(RecoveryError)


def partial_stream_body(provider: str, kind: str) -> bytes:
    deltas = {
        "content": {"content": "partial"},
        "thinking": {
            "thinking"
            if provider == "ollama"
            else "reasoning_content": "private-thought"
        },
        "tool": {
            "tool_calls": [
                {
                    "index": 0,
                    "id": "call",
                    "function": {
                        "name": "count",
                        "arguments": {"value": 7} if provider == "ollama" else "{",
                    },
                }
            ]
        },
    }
    delta = deltas[kind]
    payload = (
        {"message": {"role": "assistant", **delta}, "done": False}
        if provider == "ollama"
        else {"choices": [{"delta": delta}]}
    )
    raw = json.dumps(payload).encode()
    return raw + b"\n" if provider == "ollama" else b"data: " + raw + b"\n\n"


class DescribeReadinessBoundary:
    @pytest.mark.parametrize("provider", ["ollama", "omlx", "openai", "anthropic"])
    @pytest.mark.parametrize("route", ["broker", "session"])
    @pytest.mark.parametrize("status", [500, 502])
    @pytest.mark.parametrize(
        "selection,eligible",
        [("default", True), ("status", False), ("category", False)],
    )
    def should_apply_selected_eligibility_and_recover_server_errors(
        self, provider, route, status, selection, eligible
    ):
        lifecycle = []
        controls = {
            "status": {"retryable_statuses": frozenset()},
            "category": {"retryable_categories": frozenset()},
            "default": {},
        }
        policy = RecoveryPolicy(
            max_attempts=2,
            base_delay=0,
            admission=allow,
            observer=lifecycle.append,
            **controls[selection],
        )
        with scripted_http(
            [
                (status, {}, b"private-error"),
                (200, {}, response_body(provider, "ordinary")),
            ]
        ) as (host, requests):
            broker = LLMBroker(
                model="test", gateway=gateway_for(provider, host, policy)
            )
            session = ChatSession(broker, system_prompt="system", config=CONFIG)

            invoke = {
                "broker": lambda: broker.generate(
                    [LLMMessage(content="prompt")], config=CONFIG
                ),
                "session": lambda: session.send("prompt"),
            }[route]
            with outcome_context(eligible):
                assert invoke() == "sentinel"

        failed = next(
            event for event in lifecycle if event.transition == "attempt_failed"
        )
        assert failed.failure.http_status == status
        assert failed.failure.category == "http"
        assert failed.failure.operation == "ordinary"
        assert failed.failure.phase == "decoding"
        assert failed.failure.acceptance == "unknown"
        assert failed.failure.eligible == eligible
        assert (
            failed.failure.reason == {True: "transient", False: "permanent"}[eligible]
        )
        assert failed.delay is None
        assert requests[0][:2] == expected_request(provider, "ordinary", route)
        assert [request[:2] for request in requests] == [requests[0][:2]] * {
            True: 2,
            False: 1,
        }[eligible]
        assert [
            event.delay for event in lifecycle if event.transition == "delay_scheduled"
        ] == {True: [0], False: []}[eligible]
        assert "private-error" not in repr(lifecycle)

    @pytest.mark.parametrize("provider", ["ollama", "omlx", "openai"])
    @pytest.mark.parametrize("route", ["broker", "session"])
    @pytest.mark.parametrize(
        "kind,field",
        [
            ("content", "observed_content"),
            ("thinking", "observed_reasoning"),
            ("tool", "observed_tool_fragments"),
        ],
    )
    def should_surface_partial_semantics_without_replay_through_public_streams(
        self, provider, route, kind, field
    ):
        body = partial_stream_body(provider, kind)
        lifecycle = []
        policy = RecoveryPolicy(
            max_attempts=2, admission=allow, observer=lifecycle.append
        )
        with scripted_http([(200, {"Content-Length": str(len(body) + 100)}, body)]) as (
            host,
            requests,
        ):
            broker = LLMBroker(
                model="test", gateway=gateway_for(provider, host, policy)
            )
            session = ChatSession(broker, system_prompt="system", config=CONFIG)
            stream = {
                "broker": lambda: broker.generate_stream(
                    [LLMMessage(content="prompt")], config=CONFIG
                ),
                "session": lambda: session.send_stream("prompt"),
            }[route]()

            with pytest.raises(RecoveryError) as caught:
                list(stream)

        failure = caught.value.report.final_failure
        assert caught.value.report.outcome == "interrupted"
        assert failure.reason == "semantic_output"
        assert getattr(failure.progress, field) > 0
        assert failure.category == "transport"
        assert failure.operation == "streaming"
        assert failure.phase == "streaming"
        assert failure.acceptance == "unknown"
        assert not failure.eligible
        assert caught.value.inspect_response() == body
        assert [request[:2] for request in requests] == [
            expected_request(provider, "streaming", route)
        ]
        assert lifecycle[-1].transition == "interrupted"
        assert lifecycle[-1].delay is None
        assert lifecycle[-1].failure == failure
        assert "private-thought" not in repr(lifecycle)
        assert [message.content for message in session.messages] == ["system"] + {
            "session": ["prompt"],
            "broker": [],
        }[route]
