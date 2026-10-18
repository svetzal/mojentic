"""Admission contract v2 (retaining v1 cases): public recovery APIs over in-process HTTP transports."""

import asyncio
import json

import httpx
import pytest
from pydantic import BaseModel, model_validator

from mojentic.llm.gateways.anthropic import AnthropicGateway
from mojentic.llm.gateways.cloud_recovery_spec import success as cloud_success
from mojentic.llm.gateways.models import LLMMessage
from mojentic.llm.gateways.ollama import OllamaGateway
from mojentic.llm.gateways.ollama_recovery_spec import frame, scripted_http
from mojentic.llm.gateways.omlx import OMLXGateway
from mojentic.llm.gateways.omlx_recovery_spec import Result, completion, stream
from mojentic.llm.gateways.openai import OpenAIGateway
from mojentic.llm.recovery import RecoveryCall, RecoveryError, RecoveryPolicy
from scripts.inprocess_http import clock, virtual_sleep

CASES = [
    (provider, operation)
    for provider in ("ollama", "omlx", "openai", "anthropic")
    for operation in (
        ("ordinary",)
        if provider == "anthropic"
        else ("ordinary", "structured", "streaming")
    )
]


def gateway_for(provider, host, policy, call):
    if provider == "ollama":
        return OllamaGateway(host=host, recovery_policy=policy, recovery_call=call)
    if provider == "omlx":
        return OMLXGateway(host=host, recovery_policy=policy, recovery_call=call)
    gateway_class = {"openai": OpenAIGateway, "anthropic": AnthropicGateway}[provider]
    return gateway_class(
        api_key="credential-sentinel",
        base_url=host,
        recovery_policy=policy,
        recovery_call=call,
    )


def response_for(provider, operation):
    content = '{"answer":"answer"}' if operation == "structured" else "answer"
    if provider == "ollama":
        return frame(content) + b"\n"
    if provider == "omlx":
        return stream() if operation == "streaming" else completion(content)
    return cloud_success("anthropic" if provider == "anthropic" else operation)


async def invoke(gateway, operation):
    args = {"model": "test", "messages": [LLMMessage(content="private-payload")]}
    if operation == "streaming":
        events = [
            event async for event in gateway.complete_stream_with_recovery(**args)
        ]
        terminal = events[-1]
        assert terminal.outcome.value == terminal.report.outcome
        assert terminal.identity == terminal.report.identity
        assert (
            len([event for event in events if event.kind in {"failed", "completed"}])
            == 1
        )
        return terminal.report
    if operation == "structured":
        args["object_model"] = Result
    try:
        response = await gateway.complete_with_recovery(**args)
    except RecoveryError as error:
        return error.report
    return response.recovery_report


def invoke_sync(gateway, operation):
    args = {"model": "test", "messages": [LLMMessage(content="private-payload")]}
    if operation == "structured":
        args["object_model"] = Result
    if operation == "streaming":
        return list(gateway.complete_stream(**args))
    return gateway.complete(**args)


def assert_wire(requests, captures, lifecycle, report, provider, operation):
    outbound = [event for event in captures if event.kind == "request"]
    assert outbound
    assert all(event.body == outbound[0].body for event in outbound)
    assert all(body == outbound[0].body for path, body, headers in requests)
    payload = json.loads(outbound[0].body)
    assert payload["messages"] == [{"role": "user", "content": "private-payload"}]
    assert payload["model"] == "test"
    expected_path = {
        "ollama": "/api/chat",
        "omlx": "/v1/chat/completions",
        "openai": "/chat/completions",
        "anthropic": "/v1/messages",
    }[provider]
    assert all(path == expected_path for path, body, headers in requests)
    ids = [event.identity for event in outbound]
    assert len({identity.logical_request_id for identity in ids}) == 1
    assert len({identity.attempt_id for identity in ids}) == len(ids)
    assert [identity.wire_attempt for identity in ids] == list(range(1, len(ids) + 1))
    assert report.identity == ids[-1]
    assert lifecycle[-1].transition == {
        "succeeded": "attempt_succeeded",
        "cancelled": "cancelled",
        "interrupted": "interrupted",
    }.get(report.outcome, "exhausted")
    assert len(report.history) <= len(ids)
    for event in lifecycle:
        safe = event.model_dump_json()
        assert "private-payload" not in safe
        assert "private-error" not in safe
        assert "credential-sentinel" not in safe
        assert event.identity.logical_request_id == ids[0].logical_request_id
    for failure in report.history:
        assert failure.provider == provider
        assert failure.operation == operation


class DescribeRecoveryAdmission:
    @pytest.mark.parametrize("provider,operation", CASES)
    @pytest.mark.parametrize("decision", ["absent", "allow", "reject", None])
    async def should_apply_admission_without_changing_retry_bytes(
        self, provider, operation, decision
    ):
        lifecycle, captures = [], []
        call = RecoveryCall()

        async def admission(context):
            assert context.failure.acceptance == "unknown"
            assert context.next_attempt == 2
            assert context.previous_identity == context.failure.identity
            return decision

        policy = RecoveryPolicy(
            monotonic=clock,
            wall=lambda: 0,
            jitter=lambda ceiling: ceiling / 2,
            sleeper=virtual_sleep,
            max_attempts=2,
            base_delay=0,
            admission=None if decision == "absent" else admission,
            observer=lifecycle.append,
            wire_observer=captures.append,
        )
        retries = decision == "allow" or (
            decision == "absent" and provider in {"openai", "anthropic"}
        )
        expected = (
            "succeeded"
            if retries
            else {
                "absent": "admission_required",
                "reject": "admission_rejected",
                None: "admission_undecided",
            }[decision]
        )
        with scripted_http(
            [(503, {}, b"private-error"), (200, {}, response_for(provider, operation))]
        ) as (host, requests):
            report = await invoke(gateway_for(provider, host, policy, call), operation)

        assert report.outcome == expected
        assert len(requests) == (2 if retries else 1)
        assert report.history[0].acceptance == "unknown"
        assert report.history[0].eligible
        assert report.history[0].http_status == 503
        assert_wire(requests, captures, lifecycle, report, provider, operation)
        assert [
            event.transition
            for event in lifecycle
            if event.transition.startswith("admission_")
        ] == {
            "absent": [] if retries else ["admission_required"],
            "allow": ["admission_pending", "admission_allowed"],
            "reject": ["admission_pending", "admission_rejected"],
            None: ["admission_pending", "admission_undecided"],
        }[decision]

    @pytest.mark.parametrize("provider,operation", CASES)
    @pytest.mark.parametrize("termination", ["cancelled", "budget_exhausted"])
    async def should_stop_pending_admission(
        self, provider, operation, termination, monkeypatch
    ):
        lifecycle, captures = [], []
        call = RecoveryCall()
        hook_closed = asyncio.Event()
        from scripts.inprocess_http import VirtualClock

        loop = asyncio.get_running_loop()
        scheduler = VirtualClock()
        scheduler.now = loop.time()
        monkeypatch.setattr(loop, "time", scheduler)

        async def pending(context):
            try:
                if termination == "cancelled":
                    call.cancel()
                else:
                    scheduler.advance(1)
                await asyncio.Event().wait()
            finally:
                hook_closed.set()

        policy = RecoveryPolicy(
            monotonic=clock,
            wall=lambda: 0,
            jitter=lambda ceiling: ceiling / 2,
            sleeper=virtual_sleep,
            max_attempts=2,
            base_delay=0,
            budget=0.2,
            admission=pending,
            observer=lifecycle.append,
            wire_observer=captures.append,
        )
        with scripted_http([(503, {}, b"private-error")]) as (host, requests):
            report = await invoke(gateway_for(provider, host, policy, call), operation)

        assert report.outcome == termination
        assert hook_closed.is_set()
        assert len(requests) == 1
        assert "admission_pending" in [event.transition for event in lifecycle]
        assert_wire(requests, captures, lifecycle, report, provider, operation)

    @pytest.mark.parametrize(
        "provider,operation", [case for case in CASES if case[0] in {"ollama", "omlx"}]
    )
    async def should_retry_evidenced_connection_refusal_without_hook(
        self, provider, operation
    ):
        import errno

        from scripts.inprocess_http import Body, transport

        requests, captures, lifecycle = [], [], []
        sends = []

        async def respond(request):
            sends.append(request)
            trace = request.extensions["trace"]
            if len(sends) == 1:
                cause = ConnectionRefusedError(errno.ECONNREFUSED, "Connection refused")
                await trace("connection.connect_tcp.failed", {"exception": cause})
                raise httpx.ConnectError(
                    "Connection refused", request=request
                ) from cause
            requests.append(
                (request.url.raw_path.decode(), request.content, dict(request.headers))
            )
            return httpx.Response(
                200, stream=Body([(0, response_for(provider, operation))], {})
            )

        policy = RecoveryPolicy(
            monotonic=clock,
            wall=lambda: 0,
            jitter=lambda ceiling: ceiling / 2,
            sleeper=virtual_sleep,
            max_attempts=2,
            base_delay=0,
            observer=lifecycle.append,
            wire_observer=captures.append,
        )
        with transport(respond):
            report = await invoke(
                gateway_for(provider, "http://provider.test", policy, RecoveryCall()),
                operation,
            )

        assert report.outcome == "succeeded"
        assert report.history[0].acceptance == "no"
        assert report.history[0].category == "transport"
        assert len(requests) == 1
        assert len([event for event in captures if event.kind == "request"]) == 2
        assert_wire(requests, captures, lifecycle, report, provider, operation)

    @pytest.mark.parametrize("provider", ["ollama", "omlx", "openai"])
    async def should_never_replay_after_delivering_content(self, provider):
        lifecycle, captures, decisions = [], [], []
        bodies = {
            "ollama": b'{"done":false,"message":{"role":"assistant","content":"answer"}}\n',
            "omlx": b'data: {"choices":[{"delta":{"content":"answer"}}]}\n\n',
            "openai": b'data: {"choices":[{"delta":{"content":"answer"}}]}\n\n',
        }

        async def allow(context):
            decisions.append(context)
            return "allow"

        policy = RecoveryPolicy(
            monotonic=clock,
            wall=lambda: 0,
            jitter=lambda ceiling: ceiling / 2,
            sleeper=virtual_sleep,
            max_attempts=3,
            base_delay=0,
            admission=allow,
            observer=lifecycle.append,
            wire_observer=captures.append,
        )
        with scripted_http([(200, {}, bodies[provider])]) as (host, requests):
            gateway = gateway_for(provider, host, policy, RecoveryCall())
            events = [
                event
                async for event in gateway.complete_stream_with_recovery(
                    model="test", messages=[LLMMessage(content="private-payload")]
                )
            ]

        assert [event.text for event in events if event.kind == "content"] == ["answer"]
        assert events[-1].outcome.value == "interrupted"
        report = events[-1].report
        assert report.final_failure.progress.delivered_content == len(b"answer")
        assert not report.final_failure.eligible
        assert decisions == []
        assert len(requests) == 1
        assert_wire(requests, captures, lifecycle, report, provider, "streaming")

    @pytest.mark.parametrize("provider,operation", CASES)
    def should_surface_undecided_through_synchronous_public_apis(
        self, provider, operation
    ):
        lifecycle, captures = [], []

        async def undecided(context):
            return None

        policy = RecoveryPolicy(
            monotonic=clock,
            wall=lambda: 0,
            jitter=lambda ceiling: ceiling / 2,
            sleeper=virtual_sleep,
            max_attempts=2,
            base_delay=0,
            admission=undecided,
            observer=lifecycle.append,
            wire_observer=captures.append,
        )
        with scripted_http([(503, {}, b"private-error")]) as (host, requests):
            gateway = gateway_for(provider, host, policy, RecoveryCall())
            with pytest.raises(RecoveryError) as caught:
                invoke_sync(gateway, operation)

        report = caught.value.report
        assert report.outcome == "admission_undecided"
        assert report.final_failure.reason == "transient"
        assert len(requests) == 1
        assert "admission_undecided" in [event.transition for event in lifecycle]
        assert_wire(requests, captures, lifecycle, report, provider, operation)

    @pytest.mark.parametrize("provider,operation", CASES)
    @pytest.mark.parametrize("error_type", [httpx.ConnectError, httpx.ConnectTimeout])
    async def should_not_invent_nonacceptance_from_a_capture_hook_exception(
        self, provider, operation, error_type
    ):
        lifecycle, captures = [], []

        def capture(event):
            captures.append(event)
            if event.kind == "body":
                raise error_type("private-error")

        policy = RecoveryPolicy(
            monotonic=clock,
            wall=lambda: 0,
            jitter=lambda ceiling: ceiling / 2,
            sleeper=virtual_sleep,
            max_attempts=2,
            base_delay=0,
            observer=lifecycle.append,
            wire_observer=capture,
        )
        with scripted_http([(200, {}, response_for(provider, operation))]) as (
            host,
            requests,
        ):
            report = await invoke(
                gateway_for(provider, host, policy, RecoveryCall()), operation
            )

        assert report.outcome == "interrupted"
        assert report.final_failure.acceptance == "unknown"
        assert report.final_failure.http_status == 200
        assert isinstance(
            report.final_failure.inspect_cause().inspect_cause(), error_type
        )
        assert report.final_failure.progress.headers_received
        assert report.final_failure.progress.raw_bytes > 0
        assert not report.final_failure.eligible
        assert len(requests) == 1
        assert_wire(requests, captures, lifecycle, report, provider, operation)

    @pytest.mark.parametrize("provider", ["ollama", "omlx", "openai"])
    @pytest.mark.parametrize("error_type", [httpx.ConnectError, httpx.ConnectTimeout])
    async def should_keep_acceptance_unknown_when_caller_validation_fails(
        self, provider, error_type
    ):
        cause = error_type("private-validator-error")

        class ValidatedResult(BaseModel):
            answer: str

            @model_validator(mode="after")
            def validate_answer(self):
                raise cause

        policy = RecoveryPolicy(
            monotonic=clock,
            wall=lambda: 0,
            jitter=lambda ceiling: ceiling / 2,
            sleeper=virtual_sleep,
            max_attempts=2,
            base_delay=0,
        )
        body = response_for(provider, "structured")
        with scripted_http([(200, {}, body)]) as (host, requests):
            gateway = gateway_for(provider, host, policy, RecoveryCall())
            with pytest.raises(RecoveryError) as caught:
                await gateway.complete_with_recovery(
                    model="test",
                    messages=[LLMMessage(content="private-payload")],
                    object_model=ValidatedResult,
                )

        failure = caught.value.report.final_failure
        assert failure.http_status == 200
        assert failure.progress.headers_received
        assert failure.progress.raw_bytes == len(body)
        assert failure.inspect_cause() is cause
        assert failure.acceptance == "unknown"
        assert not failure.eligible
        assert len(requests) == 1
