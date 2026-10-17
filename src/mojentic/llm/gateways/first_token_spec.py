"""Client timing measured through production HTTP, section 2."""

import asyncio
import json
import time
from pathlib import Path

import pytest

from mojentic.llm.chat_session import ChatSession
from mojentic.llm.completion_config import CompletionConfig
from mojentic.llm.gateways.models import LLMMessage
from mojentic.llm.gateways.ollama import OllamaGateway
from mojentic.llm.gateways.ollama_recovery_spec import scripted_http
from mojentic.llm.gateways.request_fidelity_spec import (
    CONTRACT,
    Count,
    gateway_for,
    reply,
)
from mojentic.llm.gateways.stream_events import CompletionMetadata
from mojentic.llm.llm_broker import LLMBroker
from mojentic.llm.recovery import RecoveryCall, RecoveryPolicy
from mojentic.llm.recovery_stream import StreamMetrics

TIMING_CONTRACT = json.loads(
    (Path(__file__).parent / "fixtures/contracts/first_token_v1.json").read_text()
)


class DescribeFirstTokenTiming:
    def should_exclude_capture_and_lazy_delay_at_actual_dispatch(self):
        def capture(event):
            if event.kind == "request":
                time.sleep(0.25)

        async def consume(host):
            gateway = OllamaGateway(
                host=host, recovery_policy=RecoveryPolicy(wire_observer=capture)
            )
            stream = gateway.complete_stream_with_recovery(
                model="test", messages=[LLMMessage(content="hello")]
            )
            await asyncio.sleep(0.25)
            return [event async for event in stream]

        body = (
            b'{"model":"test","message":{"role":"assistant","thinking":"plan",'
            b'"content":"answer"},"done":true,"done_reason":"stop",'
            b'"eval_duration":123}\n'
        )
        with scripted_http([(200, {}, (0.04, body))]) as (host, requests):
            events = asyncio.run(consume(host))

        metrics = events[-1].metrics
        assert metrics is not None
        assert metrics.first_token_kind == "thinking"
        assert 25 <= metrics.time_to_first_token_ms < 200
        assert metrics.time_to_first_token_ms <= metrics.request_duration_ms < 200
        assert metrics.eval_duration == 123
        assert requests[0][0] == "/api/chat"

    @pytest.mark.parametrize("provider", ["ollama", "omlx", "openai"])
    @pytest.mark.parametrize("route", ["events", "legacy", "broker", "session"])
    def should_measure_supported_public_routes(self, provider, route):
        with scripted_http([(200, {}, (0.03, reply(provider, "events")))]) as (
            host,
            requests,
        ):
            gateway = gateway_for(provider, host)
            metrics = public_route_metrics(gateway, route)

        assert metrics["first_token_kind"] == "content"
        assert 20 <= metrics["time_to_first_token_ms"] <= metrics["request_duration_ms"]
        assert len(requests) == 1

    @pytest.mark.parametrize("provider", ["ollama", "omlx", "openai"])
    @pytest.mark.parametrize(
        "case", TIMING_CONTRACT["cases"], ids=lambda case: case["name"]
    )
    def should_measure_first_wire_frame_and_terminal_errors(self, provider, case):
        protocol = "ollama" if provider == "ollama" else "openai"
        with scripted_http([(200, {}, (0.025, case[protocol].encode()))]) as (
            host,
            requests,
        ):
            gateway = gateway_for(provider, host)
            events = list(
                gateway.complete_stream_events(
                    "gpt-4o", [LLMMessage(content="hello")], CompletionConfig()
                )
            )

        metrics = events[-1].metadata
        expected = case["expected_kinds"][provider]
        assert metrics.first_token_kind == expected
        assert metrics.request_duration_ms >= 15
        assert (metrics.time_to_first_token_ms is None) == (expected is None)
        assert len(requests) == 1

    @pytest.mark.parametrize("provider", ["ollama", "omlx", "openai"])
    def should_include_admitted_retry_delay_on_one_clock(self, provider):
        async def admission(context):
            await asyncio.sleep(0.12)
            return "allow"

        async def consume(gateway):
            return [
                event
                async for event in gateway.complete_stream_with_recovery(
                    model="gpt-4o", messages=[LLMMessage(content="hello")]
                )
            ]

        with scripted_http(
            [
                (503, {}, b'{"error":"busy"}'),
                (200, {}, (0.03, reply(provider, "events"))),
            ]
        ) as (host, requests):
            gateway = gateway_for(provider, host)
            gateway.recovery_policy = RecoveryPolicy(
                max_attempts=2, base_delay=0, admission=admission
            )
            terminal = asyncio.run(consume(gateway))[-1]

        assert terminal.kind == "completed"
        assert terminal.metrics.first_token_kind == "content"
        assert terminal.metrics.time_to_first_token_ms >= 140
        assert (
            terminal.metrics.request_duration_ms
            >= terminal.metrics.time_to_first_token_ms
        )
        assert requests[0][1] == requests[1][1]

    @pytest.mark.parametrize("provider", ["ollama", "omlx", "openai"])
    @pytest.mark.parametrize("body", [b'{"error":"failed"}\n', b"not-json\n"])
    def should_report_dispatched_failure_without_inventing_tokens(self, provider, body):
        with scripted_http([(500, {}, (0.03, body))]) as (host, requests):
            terminal = list(
                gateway_for(provider, host).complete_stream_events(
                    "gpt-4o", [LLMMessage(content="hello")], CompletionConfig()
                )
            )[-1]

        assert terminal.type == "error"
        assert terminal.metadata.request_duration_ms >= 20
        assert terminal.metadata.first_token_kind is None
        assert terminal.metadata.time_to_first_token_ms is None
        assert len(requests) == 1

    @pytest.mark.parametrize("provider", ["ollama", "omlx", "openai"])
    def should_keep_local_close_evidence_without_a_synthetic_terminal(self, provider):
        with scripted_http([(200, {}, (0.025, reply(provider, "events")))]) as (
            host,
            requests,
        ):
            gateway = gateway_for(provider, host)
            stream = gateway.complete_stream_events(
                "gpt-4o", [LLMMessage(content="hello")], CompletionConfig()
            )
            assert next(stream).text == "answer"
            stream.close()

        assert gateway.last_stream_metrics.first_token_kind == "content"
        assert gateway.last_stream_metrics.request_duration_ms >= 15
        assert len(requests) == 1

    @pytest.mark.parametrize("provider", ["omlx", "openai"])
    def should_measure_argument_fragment_before_later_failure(self, provider):
        first = (
            b'data: {"choices":[{"index":0,"delta":{"tool_calls":[{"index":0,'
            b'"id":"call-1","type":"function","function":{"name":"count","arguments":"{"}}]}}]}\n\n'
        )
        failure = b'data: {"error":"failed"}\n\n'

        async def consume(gateway):
            return [
                event
                async for event in gateway.complete_stream_with_recovery(
                    model="gpt-4o", messages=[LLMMessage(content="hello")]
                )
            ]

        with scripted_http([(200, {}, [(0.025, first), (0.15, failure)])]) as (
            host,
            requests,
        ):
            terminal = asyncio.run(consume(gateway_for(provider, host, True)))[-1]

        assert terminal.kind == "failed"
        assert terminal.metrics.first_token_kind == "tool_call"
        assert 15 <= terminal.metrics.time_to_first_token_ms < 130
        assert (
            terminal.metrics.request_duration_ms
            >= terminal.metrics.time_to_first_token_ms + 100
        )
        assert terminal.report.progress.observed_tool_fragments == 1
        assert len(requests) == 1

    @pytest.mark.parametrize("provider", ["ollama", "omlx", "openai"])
    @pytest.mark.parametrize("recovery", [False, True])
    def should_reset_continuation_clock_and_preserve_exact_tool_history(
        self, provider, recovery
    ):
        first = streaming_tool_reply(provider)
        with scripted_http(
            [(200, {}, (0.12, first)), (200, {}, (0.025, reply(provider, "events")))]
        ) as (host, requests):
            gateway = gateway_for(provider, host, recovery)
            tool = SlowCount(gateway)
            broker = LLMBroker(model="gpt-4o", gateway=gateway)

            assert (
                "".join(
                    broker.generate_stream([LLMMessage(content="hello")], tools=[tool])
                )
                == "answer"
            )

        metrics = broker.last_stream_metrics
        assert metrics.first_token_kind == "content"
        assert 15 <= metrics.time_to_first_token_ms <= metrics.request_duration_ms < 180
        assert tool.first_metrics.first_token_kind == "tool_call"
        assert tool.first_metrics.time_to_first_token_ms >= 100
        assert tool.calls == ["next-π"]
        initial = json.loads(requests[0][1])
        continuation = json.loads(requests[1][1])
        assert continuation == initial | {
            "messages": expected_continuation(provider, recovery)
        }
        assert len(requests) == 2

    def should_not_invent_dispatch_evidence_for_unsupported_model(self):
        with scripted_http([]) as (host, requests):
            gateway = gateway_for("openai", host)
            terminal = list(
                gateway.complete_stream_events(
                    "gpt-5-pro", [LLMMessage(content="hello")], CompletionConfig()
                )
            )[-1]

        assert terminal.reason.value == "stream_events_unsupported"
        assert terminal.metadata is None
        assert requests == []

    @pytest.mark.parametrize("provider", ["ollama", "omlx", "openai"])
    @pytest.mark.parametrize("phase", ["headers", "body"])
    def should_keep_timing_on_explicit_recovery_cancellation(self, provider, phase):
        call = RecoveryCall()

        def capture(event):
            if event.kind == phase:
                call.cancel()

        async def consume(gateway):
            return [
                event
                async for event in gateway.complete_stream_with_recovery(
                    model="gpt-4o", messages=[LLMMessage(content="hello")], call=call
                )
            ]

        with scripted_http([(200, {}, (0.025, reply(provider, "events")))]) as (
            host,
            requests,
        ):
            gateway = gateway_for(provider, host)
            gateway.recovery_policy = RecoveryPolicy(wire_observer=capture)
            terminal = asyncio.run(consume(gateway))[-1]

        assert terminal.outcome.value == "cancelled"
        assert terminal.metrics.request_duration_ms >= 0
        assert (
            terminal.metrics.first_token_kind
            == {"headers": None, "body": "content"}[phase]
        )
        assert len(requests) == 1

    @pytest.mark.parametrize("provider", ["ollama", "omlx", "openai"])
    def should_not_report_duration_if_request_capture_rejects_dispatch(self, provider):
        def capture(event):
            if event.kind == "request":
                raise ValueError("capture refused")

        async def consume(gateway):
            return [
                event
                async for event in gateway.complete_stream_with_recovery(
                    model="gpt-4o", messages=[LLMMessage(content="hello")]
                )
            ]

        with scripted_http([]) as (host, requests):
            gateway = gateway_for(provider, host)
            gateway.recovery_policy = RecoveryPolicy(wire_observer=capture)
            terminal = asyncio.run(consume(gateway))[-1]

        assert terminal.kind == "failed"
        assert terminal.metrics.request_duration_ms is None
        assert terminal.metrics.first_token_kind is None
        assert requests == []

    @pytest.mark.parametrize("model", [CompletionMetadata, StreamMetrics])
    def should_accept_old_evidence_without_optional_client_fields(self, model):
        evidence = model.model_validate({})

        assert evidence.time_to_first_token_ms is None
        assert evidence.first_token_kind is None
        assert evidence.request_duration_ms is None

    @pytest.mark.parametrize("provider", ["ollama", "omlx", "openai"])
    def should_ignore_token_frames_after_terminal_proof(self, provider):
        protocol = "ollama" if provider == "ollama" else "openai"
        empty = next(
            case for case in TIMING_CONTRACT["cases"] if case["name"] == "empty-success"
        )
        payload = empty[protocol].encode() + reply(provider, "events")
        # OpenAI recovery's supported envelope has no oMLX keepalive frame.
        payload = payload.split(b"\n\n", 1)[1] if provider == "openai" else payload

        async def consume(gateway):
            return [
                event
                async for event in gateway.complete_stream_with_recovery(
                    model="gpt-4o", messages=[LLMMessage(content="hello")]
                )
            ]

        with scripted_http([(200, {}, (0.025, payload))]) as (host, requests):
            terminal = asyncio.run(consume(gateway_for(provider, host, True)))[-1]

        assert terminal.kind == "completed"
        assert terminal.metrics.first_token_kind is None
        assert terminal.metrics.time_to_first_token_ms is None
        assert terminal.metrics.request_duration_ms >= 15
        assert len(requests) == 1


class SlowCount(Count):
    def __init__(self, gateway):
        super().__init__()
        self.gateway = gateway
        self.first_metrics = None

    def run(self, value: str) -> str:
        self.first_metrics = self.gateway.last_stream_metrics
        time.sleep(0.2)
        return super().run(value)


def streaming_tool_reply(provider: str) -> bytes:
    call = json.loads(json.dumps(CONTRACT["tool_call"]))
    if provider == "ollama":
        call["function"]["arguments"] = {"value": "next-π"}
        frame = {
            "model": "gpt-4o",
            "message": {"role": "assistant", "content": "", "tool_calls": [call]},
            "done": True,
            "done_reason": "stop",
        }
        return (json.dumps(frame) + "\n").encode()
    call["index"] = 0
    frame = {
        "choices": [
            {"index": 0, "delta": {"tool_calls": [call]}, "finish_reason": "tool_calls"}
        ]
    }
    return ("data: " + json.dumps(frame) + "\n\ndata: [DONE]\n\n").encode()


def expected_continuation(provider: str, recovery: bool) -> list[dict]:
    call = json.loads(json.dumps(CONTRACT["tool_call"]))
    if provider == "ollama":
        call["function"]["arguments"] = {"value": "next-π"}
        assistant = {"role": "assistant", "content": "", "tool_calls": [call]}
        if not recovery:
            assistant = {
                "role": "assistant",
                "tool_calls": [{"function": call["function"]}],
            }
        return [
            {"role": "user", "content": "hello"},
            assistant,
            {"role": "tool", "content": json.dumps("next-π")},
        ]
    call["function"]["arguments"] = json.dumps({"value": "next-π"})
    return [
        {"role": "user", "content": "hello"},
        {"role": "assistant", "content": "", "tool_calls": [call]},
        {"role": "tool", "content": json.dumps("next-π"), "tool_call_id": call["id"]},
    ]


def public_route_metrics(gateway, route: str) -> dict:
    broker = LLMBroker(model="gpt-4o", gateway=gateway)
    messages = [LLMMessage(content="hello")]
    if route == "events":
        terminal = list(
            gateway.complete_stream_events("gpt-4o", messages, CompletionConfig())
        )[-1]
        return terminal.metadata.model_dump()
    if route == "legacy":
        chunks = list(gateway.complete_stream(model="gpt-4o", messages=messages))
        assert "".join(chunk.content or "" for chunk in chunks) == "answer"
        return gateway.last_stream_metrics.model_dump()
    if route == "broker":
        assert "".join(broker.generate_stream(messages)) == "answer"
        return broker.last_stream_metrics.model_dump()
    session = ChatSession(broker)
    assert "".join(session.send_stream("hello")) == "answer"
    return session.last_stream_metrics.model_dump()
