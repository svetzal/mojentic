"""Client timing measured through production gateways with virtual timing, section 2."""

import asyncio
import json
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
from mojentic.llm.gateways.stream_events import (
    CompletionMetadata,
    StreamContent,
    StreamError,
    StreamErrorReason,
)
from mojentic.llm.llm_broker import LLMBroker
from mojentic.llm.recovery import RecoveryCall, RecoveryPolicy
from mojentic.llm.recovery_stream import StreamMetrics
from scripts.inprocess_http import InProcessTokenizer, clock, virtual_sleep

TIMING_CONTRACT = json.loads(
    (Path(__file__).parent / "fixtures/contracts/first_token_v1.json").read_text()
)


@pytest.fixture
def incomplete_stream(provider):
    if provider == "ollama":
        body = (
            b'{"model":"test","message":{"role":"assistant","content":"answer"},'
            b'"done":false,"eval_duration":123}\n'
        )
        expected = {"eval_duration": 123}
    else:
        body = (
            b'data: {"choices":[{"index":0,"delta":{"content":"answer"}}],'
            b'"usage":{"prompt_tokens":2,"completion_tokens":3,"total_tokens":5}}\n\n'
        )
        expected = {
            "usage": {"prompt_tokens": 2, "completion_tokens": 3, "total_tokens": 5}
        }
    return body, expected


class DescribeFirstTokenTiming:
    @pytest.mark.parametrize("provider", ["openai", "omlx"])
    def should_preserve_invalid_stream_event_for_noniterable_choices(self, provider):
        body = b'data: {"choices":1}\n\n'
        with scripted_http([(200, {}, (0.03125, body))]) as (host, requests):
            gateway = gateway_for(provider, host)
            events = list(
                gateway.complete_stream_events(
                    "gpt-4o", [LLMMessage(content="hello")], CompletionConfig()
                )
            )

        assert len(events) == 1
        assert isinstance(events[0], StreamError)
        assert events[0].reason == StreamErrorReason.INVALID_STREAM_EVENT
        assert events[0].metadata.request_duration_ms == 31.25
        assert events[0].metadata.time_to_first_token_ms is None
        assert events[0].metadata.first_token_kind is None
        assert len(requests) == 1

    @pytest.mark.parametrize("provider", ["openai", "omlx"])
    def should_preserve_content_timing_before_invalid_choices(self, provider):
        content = b'data: {"choices":[{"index":0,"delta":{"content":"answer"}}]}\n\n'
        invalid = b'data: {"choices":1}\n\n'
        with scripted_http([(200, {}, [(0.03125, content), (0.0625, invalid)])]) as (
            host,
            requests,
        ):
            gateway = gateway_for(provider, host)
            events = list(
                gateway.complete_stream_events(
                    "gpt-4o", [LLMMessage(content="hello")], CompletionConfig()
                )
            )

        assert len(events) == 2
        assert events[0] == StreamContent(text="answer")
        assert isinstance(events[1], StreamError)
        assert events[1].reason == StreamErrorReason.INVALID_STREAM_EVENT
        assert events[1].metadata.first_token_kind == "content"
        assert events[1].metadata.time_to_first_token_ms == 31.25
        assert events[1].metadata.request_duration_ms == 93.75
        assert len(requests) == 1

    @pytest.mark.parametrize("provider", ["ollama", "omlx", "openai"])
    @pytest.mark.parametrize("route", ["legacy", "broker", "session"])
    def should_retain_recovery_timing_immediately_after_public_close(
        self, provider, route, incomplete_stream
    ):
        body, expected = incomplete_stream
        with scripted_http([(200, {}, [(0.03125, body), (0.25, b"\n")])]) as (
            host,
            requests,
        ):
            gateway = gateway_for(provider, host, True)
            broker = LLMBroker(
                tokenizer=InProcessTokenizer(), model="gpt-4o", gateway=gateway
            )
            owner, stream = close_route(gateway, broker, route)

            chunk = next(stream)
            assert (chunk.content if route == "legacy" else chunk) == "answer"
            stream.close()
            metrics = owner.last_stream_metrics
            assert metrics is not None
            assert metrics.first_token_kind == "content"
            assert (
                metrics.time_to_first_token_ms == metrics.request_duration_ms == 31.25
            )
            assert metrics.metadata == expected
            assert len(requests) == 1

    @pytest.mark.parametrize("provider", ["ollama", "omlx", "openai"])
    @pytest.mark.parametrize("route", ["legacy", "broker", "session"])
    def should_leave_unsent_recovery_close_without_timing(self, provider, route):
        with scripted_http([]) as (host, requests):
            gateway = gateway_for(provider, host, True)
            broker = LLMBroker(
                tokenizer=InProcessTokenizer(), model="gpt-4o", gateway=gateway
            )
            owner, stream = close_route(gateway, broker, route)

            stream.close()

            assert getattr(owner, "last_stream_metrics", None) is None
            assert requests == []

    def should_exclude_capture_and_lazy_delay_at_actual_dispatch(self):
        def capture(event):
            if event.kind == "request":
                clock.advance(0.25)

        async def consume(host):
            gateway = OllamaGateway(
                host=host,
                recovery_policy=RecoveryPolicy(
                    monotonic=clock,
                    wall=lambda: 0,
                    jitter=lambda ceiling: ceiling / 2,
                    sleeper=virtual_sleep,
                    wire_observer=capture,
                ),
            )
            stream = gateway.complete_stream_with_recovery(
                model="test", messages=[LLMMessage(content="hello")]
            )
            clock.advance(0.25)
            return [event async for event in stream]

        body = (
            b'{"model":"test","message":{"role":"assistant","thinking":"plan",'
            b'"content":"answer"},"done":true,"done_reason":"stop",'
            b'"eval_duration":123}\n'
        )
        with scripted_http([(200, {}, (0.0625, body))]) as (host, requests):
            events = asyncio.run(consume(host))

        metrics = events[-1].metrics
        assert metrics is not None
        assert metrics.first_token_kind == "thinking"
        assert metrics.time_to_first_token_ms == 62.5
        assert metrics.request_duration_ms == 62.5
        assert metrics.eval_duration == 123
        assert requests[0][0] == "/api/chat"

    @pytest.mark.parametrize("provider", ["ollama", "omlx", "openai"])
    @pytest.mark.parametrize("route", ["events", "legacy", "broker", "session"])
    def should_measure_supported_public_routes(self, provider, route):
        with scripted_http([(200, {}, (0.03125, reply(provider, "events")))]) as (
            host,
            requests,
        ):
            gateway = gateway_for(provider, host)
            metrics = public_route_metrics(gateway, route)

        assert metrics["first_token_kind"] == "content"
        assert (
            metrics["time_to_first_token_ms"] == metrics["request_duration_ms"] == 31.25
        )
        assert len(requests) == 1

    @pytest.mark.parametrize("provider", ["ollama", "omlx", "openai"])
    @pytest.mark.parametrize(
        "case", TIMING_CONTRACT["cases"], ids=lambda case: case["name"]
    )
    def should_measure_first_wire_frame_and_terminal_errors(self, provider, case):
        protocol = "ollama" if provider == "ollama" else "openai"
        with scripted_http([(200, {}, (0.03125, case[protocol].encode()))]) as (
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
        assert metrics.request_duration_ms == 31.25
        assert (
            metrics.time_to_first_token_ms
            == {None: None, "content": 31.25, "thinking": 31.25, "tool_call": 31.25}[
                expected
            ]
        )
        assert len(requests) == 1

    @pytest.mark.parametrize("provider", ["ollama", "omlx", "openai"])
    def should_include_admitted_retry_delay_on_one_clock(self, provider):
        async def admission(context):
            clock.advance(0.125)
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
                (200, {}, (0.03125, reply(provider, "events"))),
            ]
        ) as (host, requests):
            gateway = gateway_for(provider, host)
            gateway.recovery_policy = RecoveryPolicy(
                monotonic=clock,
                wall=lambda: 0,
                jitter=lambda ceiling: ceiling / 2,
                sleeper=virtual_sleep,
                max_attempts=2,
                base_delay=0,
                admission=admission,
            )
            terminal = asyncio.run(consume(gateway))[-1]

        assert terminal.kind == "completed"
        assert terminal.metrics.first_token_kind == "content"
        assert terminal.metrics.time_to_first_token_ms == 156.25
        assert terminal.metrics.request_duration_ms == 156.25
        assert requests[0][1] == requests[1][1]

    @pytest.mark.parametrize("provider", ["ollama", "omlx", "openai"])
    @pytest.mark.parametrize("body", [b'{"error":"failed"}\n', b"not-json\n"])
    def should_report_dispatched_failure_without_inventing_tokens(self, provider, body):
        with scripted_http([(500, {}, (0.03125, body))]) as (host, requests):
            terminal = list(
                gateway_for(provider, host).complete_stream_events(
                    "gpt-4o", [LLMMessage(content="hello")], CompletionConfig()
                )
            )[-1]

        assert terminal.type == "error"
        assert terminal.metadata.request_duration_ms == 31.25
        assert terminal.metadata.first_token_kind is None
        assert terminal.metadata.time_to_first_token_ms is None
        assert len(requests) == 1

    @pytest.mark.parametrize("provider", ["ollama", "omlx", "openai"])
    def should_keep_local_close_evidence_without_a_synthetic_terminal(self, provider):
        with scripted_http([(200, {}, (0.03125, reply(provider, "events")))]) as (
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
        assert gateway.last_stream_metrics.request_duration_ms == 31.25
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

        with scripted_http([(200, {}, [(0.03125, first), (0.1875, failure)])]) as (
            host,
            requests,
        ):
            terminal = asyncio.run(consume(gateway_for(provider, host, True)))[-1]

        assert terminal.kind == "failed"
        assert terminal.metrics.first_token_kind == "tool_call"
        assert terminal.metrics.time_to_first_token_ms == 31.25
        assert terminal.metrics.request_duration_ms == 218.75
        assert terminal.report.progress.observed_tool_fragments == 1
        assert len(requests) == 1

    @pytest.mark.parametrize("provider", ["ollama", "omlx", "openai"])
    @pytest.mark.parametrize("recovery", [False, True])
    def should_reset_continuation_clock_and_preserve_exact_tool_history(
        self, provider, recovery
    ):
        first = streaming_tool_reply(provider)
        with scripted_http(
            [(200, {}, (0.125, first)), (200, {}, (0.03125, reply(provider, "events")))]
        ) as (host, requests):
            gateway = gateway_for(provider, host, recovery)
            tool = SlowCount(gateway)
            broker = LLMBroker(
                tokenizer=InProcessTokenizer(), model="gpt-4o", gateway=gateway
            )

            assert (
                "".join(
                    broker.generate_stream([LLMMessage(content="hello")], tools=[tool])
                )
                == "answer"
            )

        metrics = broker.last_stream_metrics
        assert metrics.first_token_kind == "content"
        assert metrics.time_to_first_token_ms == metrics.request_duration_ms == 31.25
        assert tool.first_metrics.first_token_kind == "tool_call"
        assert tool.first_metrics.time_to_first_token_ms == 125
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

        with scripted_http([(200, {}, (0.03125, reply(provider, "events")))]) as (
            host,
            requests,
        ):
            gateway = gateway_for(provider, host)
            gateway.recovery_policy = RecoveryPolicy(
                monotonic=clock,
                wall=lambda: 0,
                jitter=lambda ceiling: ceiling / 2,
                sleeper=virtual_sleep,
                wire_observer=capture,
            )
            terminal = asyncio.run(consume(gateway))[-1]

        assert terminal.outcome.value == "cancelled"
        assert terminal.metrics.request_duration_ms == 31.25
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
            gateway.recovery_policy = RecoveryPolicy(
                monotonic=clock,
                wall=lambda: 0,
                jitter=lambda ceiling: ceiling / 2,
                sleeper=virtual_sleep,
                wire_observer=capture,
            )
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

        with scripted_http([(200, {}, (0.03125, payload))]) as (host, requests):
            terminal = asyncio.run(consume(gateway_for(provider, host, True)))[-1]

        assert terminal.kind == "completed"
        assert terminal.metrics.first_token_kind is None
        assert terminal.metrics.time_to_first_token_ms is None
        assert terminal.metrics.request_duration_ms == 31.25
        assert len(requests) == 1


class SlowCount(Count):
    def __init__(self, gateway):
        super().__init__()
        self.gateway = gateway
        self.first_metrics = None

    def run(self, value: str) -> str:
        self.first_metrics = self.gateway.last_stream_metrics
        clock.advance(0.2)
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


def close_route(gateway, broker, route):
    messages = [LLMMessage(content="hello")]
    if route == "legacy":
        return gateway, gateway.complete_stream(model="gpt-4o", messages=messages)
    if route == "broker":
        return broker, broker.generate_stream(messages)
    session = ChatSession(broker, tokenizer_gateway=InProcessTokenizer())
    return session, session.send_stream("hello")


def public_route_metrics(gateway, route: str) -> dict:
    broker = LLMBroker(tokenizer=InProcessTokenizer(), model="gpt-4o", gateway=gateway)
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
    session = ChatSession(broker, tokenizer_gateway=InProcessTokenizer())
    assert "".join(session.send_stream("hello")) == "answer"
    return session.last_stream_metrics.model_dump()
