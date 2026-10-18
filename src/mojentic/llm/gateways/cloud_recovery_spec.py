"""Cloud recovery specifications at a in-process HTTP transports boundary."""

import asyncio
import json

import httpx
import pytest

from mojentic.llm.chat_session import ChatSession
from mojentic.llm.completion_config import CompletionConfig, ResponseFormat
from mojentic.llm.gateways import omlx_recovery_spec as recovery_fixtures
from mojentic.llm.gateways.anthropic import AnthropicGateway
from mojentic.llm.gateways.models import LLMMessage
from mojentic.llm.gateways.ollama_recovery_spec import scripted_http
from mojentic.llm.gateways.omlx_recovery_spec import (
    Result,
    allow,
    completion,
    reject,
    stream,
)
from mojentic.llm.gateways.openai import OpenAIGateway
from mojentic.llm.recovery import RecoveryCall, RecoveryError, RecoveryPolicy
from scripts.inprocess_http import clock, unfinished_http, virtual_sleep

counter_tool = recovery_fixtures.counter_tool
broker_factory = recovery_fixtures.broker_factory

OPERATIONS = ["ordinary", "structured", "streaming", "tool_stream", "anthropic"]
OPENAI_BODY = (
    b'{"model":"gpt-4o","messages":[{"role":"user","content":"h\xc3\xa9llo"}],'
    b'"temperature":0.25,"max_tokens":17'
)
STREAM_CONTROLS = b',"stream":true,"stream_options":{"include_usage":true}}'
EXPECTED = {
    "ordinary": OPENAI_BODY + b"}",
    "structured": b"".join(
        (
            OPENAI_BODY,
            (
                b',"response_format":{"type":"json_schema","json_schema":{"name":"Result","strict":true,"schema":'
                b'{"properties":{"answer":{"title":"Answer","type":"string"}},"required":["answer"],'
                b'"title":"Result","type":"object","additionalProperties":false}}}}'
            ),
        )
    ),
    "streaming": OPENAI_BODY + STREAM_CONTROLS,
    "tool_stream": b"".join(
        (
            OPENAI_BODY,
            (
                b',"tools":[{"type":"function","function":{"name":"counter","description":"Count once",'
                b'"parameters":{"type":"object","properties":{},"required":[]}}}]'
            ),
            STREAM_CONTROLS,
        )
    ),
    "anthropic": (
        b'{"model":"claude-test","system":null,"messages":[{"role":"user","content":"h\xc3\xa9llo"}],'
        b'"temperature":0.25,"max_tokens":17}'
    ),
}
RECOVERED = [
    "attempt_started",
    "attempt_failed",
    "admission_pending",
    "admission_allowed",
    "delay_scheduled",
    "retry_started",
    "attempt_started",
    "attempt_succeeded",
]


def cloud_gateway(host, operation, policy, call=None):
    if operation == "anthropic":
        return AnthropicGateway(
            api_key="credential-sentinel",
            base_url=host,
            recovery_policy=policy,
            recovery_call=call,
        )
    return OpenAIGateway(
        api_key="credential-sentinel",
        base_url=host + "/v1",
        recovery_policy=policy,
        recovery_call=call,
    )


def success(operation):
    if operation == "anthropic":
        return (
            b'{"id":"msg","type":"message","role":"assistant","model":"reported",'
            b'"content":[{"type":"text","text":"answer"}],"stop_reason":"end_turn",'
            b'"usage":{"input_tokens":2,"output_tokens":3}}'
        )
    if operation in {"streaming", "tool_stream"}:
        return stream("answer")
    return completion(
        '{"answer":"answer"}' if operation == "structured" else "answer"
    ).replace(b'"finish_reason": "length"', b'"finish_reason": "stop"')


async def request(gateway, operation, tool, args_override=None):
    args = {
        "model": "claude-test" if operation == "anthropic" else "gpt-4o",
        "messages": [LLMMessage(content="héllo")],
        "config": CompletionConfig(temperature=0.25, max_tokens=17),
    }
    if operation == "structured":
        args["object_model"] = Result
    if operation == "tool_stream":
        args["tools"] = [tool]
    args |= args_override or {}
    if operation in {"streaming", "tool_stream"}:
        events = [
            event async for event in gateway.complete_stream_with_recovery(**args)
        ]
        terminal = events[-1]
        assert terminal.identity == terminal.report.identity
        assert terminal.outcome.value == terminal.report.outcome
        if terminal.error is not None:
            assert terminal.response is None
            raise terminal.error
        assert terminal.kind == "completed"
        return terminal.response
    return await gateway.complete_with_recovery(**args)


def assert_wire(requests, captures, operation, count):
    path = "/v1/messages" if operation == "anthropic" else "/v1/chat/completions"
    assert [(path_, body) for path_, body, headers in requests] == [
        (path, EXPECTED[operation])
    ] * count
    sent = [event for event in captures if event.kind == "request"]
    assert [event.body for event in sent] == [EXPECTED[operation]] * count
    for received, event in zip(requests, sent, strict=True):
        headers = {key.lower(): value for key, value in received[2].items()}
        captured = dict(event.headers)
        assert headers["content-type"] == captured["content-type"] == "application/json"
        assert headers["accept-encoding"] == "identity"
        credential = "x-api-key" if operation == "anthropic" else "authorization"
        assert headers[credential] == captured[credential]
        assert "credential-sentinel" in headers[credential]


class DescribeCloudWireRecovery:
    @pytest.mark.parametrize("operation", OPERATIONS)
    async def should_reuse_frozen_literal_bytes_after_admission_mutates_caller_inputs(
        self, operation, counter_tool
    ):
        messages, config, tools = (
            [LLMMessage(content="héllo")],
            CompletionConfig(temperature=0.25, max_tokens=17),
            [counter_tool],
        )
        captures = []

        async def admit(context):
            messages[0].content = "mutated payload"
            config.temperature = 0.75
            config.max_tokens = 99
            tools.clear()
            return "allow"

        overrides = {"messages": messages, "config": config}
        overrides |= {"tool_stream": {"tools": tools}}.get(operation, {})
        with scripted_http([(503, {}, b"private"), (200, {}, success(operation))]) as (
            host,
            requests,
        ):
            policy = RecoveryPolicy(
                monotonic=clock,
                wall=lambda: 0,
                jitter=lambda ceiling: ceiling / 2,
                sleeper=virtual_sleep,
                max_attempts=2,
                base_delay=0,
                admission=admit,
                wire_observer=captures.append,
            )
            result = await request(
                cloud_gateway(host, operation, policy),
                operation,
                counter_tool,
                overrides,
            )
        assert_wire(requests, captures, operation, 2)
        assert config.max_tokens == 99
        assert messages[0].content == "mutated payload"
        assert tools == []
        assert result.recovery_report.outcome == "succeeded"

    @pytest.mark.parametrize("operation", OPERATIONS)
    async def should_leave_active_generation_without_a_fixed_read_timeout(
        self, operation, counter_tool
    ):
        captures, timeouts = [], []
        with scripted_http(
            [(200, {}, (0.05, success(operation)))], timeouts=timeouts
        ) as (host, requests):
            gateway = cloud_gateway(
                host,
                operation,
                RecoveryPolicy(
                    monotonic=clock,
                    wall=lambda: 0,
                    jitter=lambda ceiling: ceiling / 2,
                    sleeper=virtual_sleep,
                    wire_observer=captures.append,
                ),
            )
            gateway.client.timeout = httpx.Timeout(1, read=0.001)
            result = await request(gateway, operation, counter_tool)
        assert_wire(requests, captures, operation, 1)
        assert result.recovery_report.outcome == "succeeded"
        assert timeouts[0]["read"] is None

    @pytest.mark.parametrize("finish", ["length", "content_filter"])
    async def should_reject_structured_parse_finish_failures_without_a_resend(
        self, finish
    ):
        data = completion('{"answer":"partial"}').replace(
            b'"finish_reason": "length"', b'"finish_reason": "' + finish.encode() + b'"'
        )
        with scripted_http([(200, {}, data)]) as (host, requests):
            gateway = cloud_gateway(
                host,
                "structured",
                RecoveryPolicy(
                    monotonic=clock,
                    wall=lambda: 0,
                    jitter=lambda ceiling: ceiling / 2,
                    sleeper=virtual_sleep,
                    max_attempts=3,
                ),
            )
            with pytest.raises(RecoveryError) as caught:
                await gateway.complete_with_recovery(
                    model="gpt-4o",
                    messages=[LLMMessage(content="héllo")],
                    object_model=Result,
                )
        assert len(requests) == 1
        assert not caught.value.report.final_failure.eligible
        assert isinstance(caught.value.inspect_cause(), ValueError)
        assert caught.value.inspect_response() == data

    @pytest.mark.parametrize(
        "model,expected",
        [
            (
                "o1-mini",
                (
                    b'{"model":"o1-mini","messages":[{"role":"user","content":"h\xc3\xa9llo"}],'
                    b'"temperature":0.25,"max_completion_tokens":17,"reasoning_effort":"high"}'
                ),
            ),
            (
                "gpt-5",
                (
                    b'{"model":"gpt-5","messages":[{"role":"user","content":"h\xc3\xa9llo"}],'
                    b'"temperature":1.0,"max_completion_tokens":17,"reasoning_effort":"high",'
                    b'"tools":[{"type":"function","function":{"name":"counter","description":"Count once",'
                    b'"parameters":{"type":"object","properties":{},"required":[]}}}]}'
                ),
            ),
        ],
    )
    async def should_freeze_model_specific_controls_and_tool_capabilities(
        self, model, expected, counter_tool
    ):
        captures = []
        with scripted_http(
            [(503, {}, b"private"), (200, {}, completion("answer"))]
        ) as (host, requests):
            gateway = cloud_gateway(
                host,
                "ordinary",
                RecoveryPolicy(
                    monotonic=clock,
                    wall=lambda: 0,
                    jitter=lambda ceiling: ceiling / 2,
                    sleeper=virtual_sleep,
                    max_attempts=2,
                    base_delay=0,
                    wire_observer=captures.append,
                ),
            )
            result = await gateway.complete_with_recovery(
                model=model,
                messages=[LLMMessage(content="héllo")],
                tools=[counter_tool],
                config=CompletionConfig(
                    temperature=0.25, max_tokens=17, reasoning_effort="high"
                ),
            )
        assert [body for path, body, headers in requests] == [expected, expected]
        assert [event.body for event in captures if event.kind == "request"] == [
            expected,
            expected,
        ]
        assert result.content == "answer"

    @pytest.mark.parametrize("operation", OPERATIONS)
    async def should_admit_cloud_retry_without_weakening_local_admission(
        self, operation, counter_tool
    ):
        lifecycle, captures = [], []
        with scripted_http([(503, {}, b"private"), (200, {}, success(operation))]) as (
            host,
            requests,
        ):
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
            result = await request(
                cloud_gateway(host, operation, policy), operation, counter_tool
            )
        assert_wire(requests, captures, operation, 2)
        assert result.recovery_report.outcome == "succeeded"
        assert [event.transition for event in lifecycle] == [
            "attempt_started",
            "attempt_failed",
            "delay_scheduled",
            "retry_started",
            "attempt_started",
            "attempt_succeeded",
        ]

    @pytest.mark.parametrize("operation", OPERATIONS)
    @pytest.mark.parametrize(
        "retry_after,state,delay",
        [
            ("2", "seconds", 2),
            ("Thu, 01 Jan 1970 00:00:03 GMT", "date", 3),
            ("invalid", "invalid", 0.5),
        ],
    )
    async def should_recover_503_with_literal_bytes_private_evidence_and_exact_lifecycle(
        self, operation, retry_after, state, delay, counter_tool
    ):
        captures, lifecycle, sleeps, admissions = [], [], [], []

        async def sleep(value):
            sleeps.append(value)

        async def admit(context):
            admissions.append(context)
            return "allow"

        policy = RecoveryPolicy(
            monotonic=clock,
            max_attempts=2,
            base_delay=4,
            jitter=lambda ceiling: 0.5,
            wall=lambda: 0,
            sleeper=sleep,
            admission=admit,
            observer=lifecycle.append,
            wire_observer=captures.append,
        )
        with scripted_http(
            [
                (
                    503,
                    {"Retry-After": retry_after, "X-Private": "credential-sentinel"},
                    b"private-body",
                ),
                (200, {}, success(operation)),
            ]
        ) as (host, requests):
            result = await request(
                cloud_gateway(host, operation, policy), operation, counter_tool
            )
        assert_wire(requests, captures, operation, 2)
        report = result.recovery_report
        assert report.outcome == "succeeded"
        assert len(report.history) == 1
        failure = report.history[0]
        assert failure.provider == (
            "anthropic" if operation == "anthropic" else "openai"
        )
        assert failure.operation == {
            "tool_stream": "streaming",
            "anthropic": "ordinary",
        }.get(operation, operation)
        assert failure.http_status == 503
        assert failure.retry_after.state == state
        expected_minimum = {"seconds": 2, "date": 3, "invalid": None}[state]
        assert failure.retry_after.delay == expected_minimum
        assert failure.eligible
        assert isinstance(failure.inspect_cause(), httpx.HTTPStatusError)
        assert failure.inspect_cause().request.content == EXPECTED[operation]
        assert failure.inspect_response() == b"private-body"
        private_headers = dict(failure.inspect_cause().response.headers)
        assert private_headers["x-private"] == "credential-sentinel"
        assert report.identity.logical_request_id == failure.identity.logical_request_id
        assert report.identity.attempt_id != failure.identity.attempt_id
        assert report.identity.wire_attempt == 2
        assert failure.identity.wire_attempt == 1
        assert admissions[0].previous_identity == failure.identity
        assert admissions[0].next_attempt == 2
        assert sleeps == [delay]
        assert [event.transition for event in lifecycle] == RECOVERED
        assert [event.identity for event in lifecycle] == [failure.identity] * 6 + [
            report.identity
        ] * 2
        assert lifecycle[4].delay == delay
        assert [event.identity for event in captures if event.kind == "request"] == [
            failure.identity,
            report.identity,
        ]
        assert result.content == (
            '{"answer":"answer"}' if operation == "structured" else "answer"
        )
        if operation == "structured":
            assert result.object == Result(answer="answer")

    @pytest.mark.parametrize("operation", OPERATIONS)
    @pytest.mark.parametrize(
        "limit,expected", [("ceiling", "delay_ceiling"), ("budget", "budget_exhausted")]
    )
    async def should_refuse_retry_after_limits_before_admission(
        self, operation, limit, expected, counter_tool
    ):
        captures, lifecycle, sleeps, admissions = [], [], [], []

        async def admit(context):
            admissions.append(context)
            return "allow"

        async def sleep(value):
            sleeps.append(value)

        limits = {"ceiling": {"delay_ceiling": 1}, "budget": {"budget": 1}}[limit]
        with scripted_http([(503, {"Retry-After": "2"}, b"private")]) as (
            host,
            requests,
        ):
            policy = RecoveryPolicy(
                max_attempts=3,
                base_delay=0,
                admission=admit,
                sleeper=sleep,
                observer=lifecycle.append,
                wire_observer=captures.append,
                **limits,
            )
            with pytest.raises(RecoveryError) as caught:
                await request(
                    cloud_gateway(host, operation, policy), operation, counter_tool
                )
        assert_wire(requests, captures, operation, 1)
        assert caught.value.report.outcome == expected
        assert caught.value.report.final_failure.http_status == 503
        assert caught.value.report.final_failure.inspect_response() == b"private"
        assert isinstance(caught.value.inspect_cause(), httpx.HTTPStatusError)
        assert sleeps == admissions == []
        assert [event.transition for event in lifecycle] == [
            "attempt_started",
            "attempt_failed",
            "exhausted",
        ]
        assert all(
            event.identity == caught.value.report.identity for event in lifecycle
        )

    @pytest.mark.parametrize("operation", OPERATIONS)
    async def should_bound_504_with_complete_history(self, operation, counter_tool):
        lifecycle, captures = [], []
        with scripted_http([(504, {}, b"first"), (504, {}, b"second")]) as (
            host,
            requests,
        ):
            policy = RecoveryPolicy(
                monotonic=clock,
                wall=lambda: 0,
                jitter=lambda ceiling: ceiling / 2,
                sleeper=virtual_sleep,
                max_attempts=2,
                base_delay=0,
                admission=allow,
                observer=lifecycle.append,
                wire_observer=captures.append,
            )
            with pytest.raises(RecoveryError) as caught:
                await request(
                    cloud_gateway(host, operation, policy), operation, counter_tool
                )
        assert_wire(requests, captures, operation, 2)
        error = caught.value
        assert error.report.outcome == "attempts_exhausted"
        assert [failure.http_status for failure in error.report.history] == [504, 504]
        assert [failure.inspect_response() for failure in error.report.history] == [
            b"first",
            b"second",
        ]
        assert all(
            isinstance(failure.inspect_cause(), httpx.HTTPStatusError)
            for failure in error.report.history
        )
        first_identity, final_identity = (
            error.report.history[0].identity,
            error.report.identity,
        )
        assert first_identity.logical_request_id == final_identity.logical_request_id
        assert first_identity.attempt_id != final_identity.attempt_id
        assert error.report.history[1].identity == error.report.identity
        assert [event.transition for event in lifecycle] == RECOVERED[:-1] + [
            "attempt_failed",
            "exhausted",
        ]

    @pytest.mark.parametrize("operation", OPERATIONS)
    @pytest.mark.parametrize("admission,outcome", [(reject, "admission_rejected")])
    async def should_refuse_absent_or_rejected_admission(
        self, operation, admission, outcome, counter_tool
    ):
        lifecycle, captures = [], []
        with scripted_http([(503, {}, b"private")]) as (host, requests):
            policy = RecoveryPolicy(
                monotonic=clock,
                wall=lambda: 0,
                jitter=lambda ceiling: ceiling / 2,
                sleeper=virtual_sleep,
                max_attempts=3,
                base_delay=0,
                admission=admission,
                observer=lifecycle.append,
                wire_observer=captures.append,
            )
            with pytest.raises(RecoveryError) as caught:
                await request(
                    cloud_gateway(host, operation, policy), operation, counter_tool
                )
        assert_wire(requests, captures, operation, 1)
        assert caught.value.report.outcome == outcome
        assert caught.value.report.final_failure.eligible
        transitions = {
            "admission_required": ["admission_required"],
            "admission_rejected": ["admission_pending", "admission_rejected"],
        }[outcome]
        assert [event.transition for event in lifecycle] == [
            "attempt_started",
            "attempt_failed",
        ] + transitions + ["exhausted"]
        assert all(
            event.identity == caught.value.report.identity for event in lifecycle
        )

    @pytest.mark.parametrize("operation", OPERATIONS)
    @pytest.mark.parametrize("status", [400, 401, 403])
    async def should_keep_truncated_permanent_status_despite_transport_eligibility(
        self, operation, status, counter_tool
    ):
        lifecycle, captures, admissions = [], [], []

        async def admit(context):
            admissions.append(context)
            return "allow"

        with scripted_http(
            [(status, {"Content-Length": "100"}, b"credential-sentinel")]
        ) as (host, requests):
            policy = RecoveryPolicy(
                monotonic=clock,
                wall=lambda: 0,
                jitter=lambda ceiling: ceiling / 2,
                sleeper=virtual_sleep,
                max_attempts=3,
                base_delay=0,
                admission=admit,
                observer=lifecycle.append,
                wire_observer=captures.append,
            )
            with pytest.raises(RecoveryError) as caught:
                await request(
                    cloud_gateway(host, operation, policy), operation, counter_tool
                )
        assert_wire(requests, captures, operation, 1)
        failure = caught.value.report.final_failure
        assert failure.http_status == status
        assert failure.category == "transport"
        assert not failure.eligible
        assert failure.reason == "permanent"
        assert isinstance(failure.inspect_cause(), httpx.RemoteProtocolError)
        assert failure.inspect_response() == b"credential-sentinel"
        assert admissions == []
        assert [event.transition for event in lifecycle] == [
            "attempt_started",
            "attempt_failed",
            "exhausted",
        ]
        safe = "".join(
            (
                str(caught.value),
                repr(caught.value),
                json.dumps(caught.value.report.model_dump(mode="json")),
            )
        )
        safe += "".join(
            (
                repr(lifecycle),
                json.dumps([event.model_dump(mode="json") for event in lifecycle]),
            )
        )
        assert "credential-sentinel" not in safe
        assert "héllo" not in safe

    @pytest.mark.parametrize("operation", OPERATIONS)
    async def should_not_follow_redirects(self, operation, counter_tool):
        captures = []
        with scripted_http([(307, {"Location": "/leak"}, b"private")]) as (
            host,
            requests,
        ):
            policy = RecoveryPolicy(
                monotonic=clock,
                wall=lambda: 0,
                jitter=lambda ceiling: ceiling / 2,
                sleeper=virtual_sleep,
                max_attempts=3,
                admission=allow,
                wire_observer=captures.append,
            )
            with pytest.raises(RecoveryError) as caught:
                await request(
                    cloud_gateway(host, operation, policy), operation, counter_tool
                )
        assert_wire(requests, captures, operation, 1)
        assert caught.value.report.final_failure.http_status == 307
        assert isinstance(caught.value.inspect_cause(), httpx.HTTPStatusError)


class DescribeCloudCancellation:
    @pytest.mark.parametrize("operation", OPERATIONS)
    async def should_cancel_an_active_request_and_close_the_owned_transport(
        self, operation, counter_tool
    ):
        call, captures, lifecycle = RecoveryCall(), [], []
        with unfinished_http() as (host, requests, started, closed):
            policy = RecoveryPolicy(
                monotonic=clock,
                wall=lambda: 0,
                jitter=lambda ceiling: ceiling / 2,
                sleeper=virtual_sleep,
                max_attempts=3,
                admission=allow,
                observer=lifecycle.append,
                wire_observer=captures.append,
            )
            task = asyncio.create_task(
                request(
                    cloud_gateway(host, operation, policy, call),
                    operation,
                    counter_tool,
                )
            )
            await started.wait()
            assert_wire(requests, captures, operation, 1)
            call.cancel()
            with pytest.raises(RecoveryError) as caught:
                await task
            await closed.wait()
        assert_wire(requests, captures, operation, 1)
        assert isinstance(caught.value.inspect_cause(), asyncio.CancelledError)
        assert caught.value.report.outcome == "cancelled"
        assert [event.transition for event in lifecycle] == [
            "attempt_started",
            "attempt_failed",
            "cancelled",
        ]

    async def should_close_a_paused_openai_consumer_without_explicit_cancellation(self):
        initial = b'data: {"choices":[{"delta":{"content":"observed"}}]}\n\n'
        lifecycle = []
        with unfinished_http(initial) as (host, requests, _started, closed):
            gateway = cloud_gateway(
                host,
                "streaming",
                RecoveryPolicy(
                    monotonic=clock,
                    wall=lambda: 0,
                    jitter=lambda ceiling: ceiling / 2,
                    sleeper=virtual_sleep,
                    max_attempts=3,
                    observer=lifecycle.append,
                ),
            )
            iterator = gateway.complete_stream_with_recovery(
                model="gpt-4o",
                messages=[LLMMessage(content="héllo")],
                config=CompletionConfig(temperature=1.0, max_tokens=16384),
            )
            first = await anext(iterator)
            assert first.kind == "progress"
            assert first.progress.observed_content
            assert first.progress.delivered_content == 0
            await iterator.aclose()
            await closed.wait()
        assert len(requests) == 1
        assert [event.transition for event in lifecycle] == [
            "attempt_started",
            "attempt_failed",
            "cancelled",
        ]

    @pytest.mark.parametrize("operation", OPERATIONS)
    @pytest.mark.parametrize("phase", ["admission", "backoff"])
    async def should_cancel_owned_admission_or_backoff(
        self, operation, phase, counter_tool
    ):
        entered, closed = asyncio.Event(), asyncio.Event()
        lifecycle, captures, call = [], [], RecoveryCall()

        async def pending(value):
            entered.set()
            try:
                await asyncio.Event().wait()
            finally:
                closed.set()

        policy = RecoveryPolicy(
            monotonic=clock,
            wall=lambda: 0,
            jitter=lambda ceiling: ceiling / 2,
            max_attempts=3,
            base_delay=0,
            observer=lifecycle.append,
            wire_observer=captures.append,
            admission={"admission": pending, "backoff": allow}[phase],
            sleeper={"admission": asyncio.sleep, "backoff": pending}[phase],
        )
        with scripted_http([(504, {}, b"private")]) as (host, requests):
            task = asyncio.create_task(
                request(
                    cloud_gateway(host, operation, policy, call),
                    operation,
                    counter_tool,
                )
            )
            await entered.wait()
            assert not task.done()
            assert_wire(requests, captures, operation, 1)
            call.cancel()
            with pytest.raises(RecoveryError) as caught:
                await task
        assert closed.is_set()
        assert_wire(requests, captures, operation, 1)
        error = caught.value
        assert error.report.outcome == "cancelled"
        assert error.report.history[0].http_status == 504
        assert isinstance(error.inspect_cause(0), httpx.HTTPStatusError)
        assert isinstance(error.inspect_cause(), asyncio.CancelledError)
        assert error.report.history[0].identity == error.report.identity
        expected = ["attempt_started", "attempt_failed", "admission_pending"]
        if phase == "backoff":
            expected += ["admission_allowed", "delay_scheduled"]
        assert [event.transition for event in lifecycle] == expected + ["cancelled"]

    @pytest.mark.parametrize("operation", OPERATIONS)
    async def should_keep_admission_pending_until_an_explicit_decision(
        self, operation, counter_tool
    ):
        entered, release = asyncio.Event(), asyncio.Event()
        captures = []

        async def admit(context):
            assert context.next_attempt == 2
            assert context.previous_identity == context.failure.identity
            entered.set()
            await release.wait()
            return "allow"

        with scripted_http([(503, {}, b"private"), (200, {}, success(operation))]) as (
            host,
            requests,
        ):
            policy = RecoveryPolicy(
                monotonic=clock,
                wall=lambda: 0,
                jitter=lambda ceiling: ceiling / 2,
                sleeper=virtual_sleep,
                max_attempts=2,
                base_delay=0,
                admission=admit,
                wire_observer=captures.append,
            )
            task = asyncio.create_task(
                request(cloud_gateway(host, operation, policy), operation, counter_tool)
            )
            await entered.wait()
            assert_wire(requests, captures, operation, 1)
            assert not task.done()
            release.set()
            result = await task
        assert_wire(requests, captures, operation, 2)
        assert result.recovery_report.outcome == "succeeded"


class DescribeCloudPrivacy:
    @pytest.mark.parametrize("operation", OPERATIONS)
    async def should_keep_header_and_payload_echoes_private_across_safe_surfaces(
        self, operation, counter_tool, caplog
    ):
        lifecycle, captures = [], []
        secret = "credential-sentinel"
        data = b'{"error":{"code":"credential-sentinel","message":"h\xc3\xa9llo credential-sentinel"}}'
        with scripted_http(
            [(503, {"X-Request-ID": secret, "Warning": secret}, data)]
        ) as (host, requests):
            policy = RecoveryPolicy(
                monotonic=clock,
                wall=lambda: 0,
                jitter=lambda ceiling: ceiling / 2,
                sleeper=virtual_sleep,
                observer=lifecycle.append,
                wire_observer=captures.append,
            )
            with pytest.raises(RecoveryError) as caught:
                await request(
                    cloud_gateway(host, operation, policy), operation, counter_tool
                )
        assert_wire(requests, captures, operation, 1)
        error = caught.value
        safe = "".join(
            (
                str(error),
                repr(error),
                repr(error.report),
                error.report.model_dump_json(),
            )
        )
        safe += "".join(
            (
                repr(lifecycle),
                "".join(event.model_dump_json() for event in lifecycle),
                caplog.text,
            )
        )
        assert secret not in safe
        assert "héllo" not in safe
        assert error.inspect_response() == data
        assert ("warning", secret) in error.inspect_headers()
        assert error.inspect_cause().request.content == EXPECTED[operation]
        assert (
            b"".join(event.body for event in captures if event.kind == "body") == data
        )

    async def should_observe_anthropic_text_before_capture_failure_without_delivery(
        self,
    ):
        data, cause, lifecycle = (
            success("anthropic"),
            OSError("credential-sentinel"),
            [],
        )

        def capture(event):
            if event.kind == "body":
                raise cause

        with scripted_http([(200, {}, data)]) as (host, requests):
            gateway = cloud_gateway(
                host,
                "anthropic",
                RecoveryPolicy(
                    monotonic=clock,
                    wall=lambda: 0,
                    jitter=lambda ceiling: ceiling / 2,
                    sleeper=virtual_sleep,
                    max_attempts=3,
                    wire_observer=capture,
                    observer=lifecycle.append,
                ),
            )
            with pytest.raises(RecoveryError) as caught:
                await gateway.complete_with_recovery(
                    model="claude-test", messages=[LLMMessage(content="héllo")]
                )
        failure = caught.value.report.final_failure
        assert len(requests) == 1
        assert failure.progress.observed_content
        assert failure.progress.delivered_content == 0
        assert caught.value.inspect_cause().inspect_cause() is cause
        assert caught.value.inspect_response() == data
        assert [event.transition for event in lifecycle] == [
            "attempt_started",
            "attempt_failed",
            "interrupted",
        ]


class DescribeOpenAIStructuredBoundary:
    async def should_preserve_openai_sdk_strict_tool_requirement_for_structured_parsing(
        self, counter_tool
    ):
        with scripted_http([(200, {}, success("structured"))]) as (host, requests):
            gateway = OpenAIGateway(api_key="private-key", base_url=host + "/v1")
            args = {
                "model": "gpt-4o",
                "messages": [LLMMessage(content="héllo")],
                "object_model": Result,
                "tools": [counter_tool],
            }
            with pytest.raises(ValueError, match="not strict"):
                gateway.complete(**args)
            assert requests == []
            gateway.recovery_policy = RecoveryPolicy(
                monotonic=clock,
                wall=lambda: 0,
                jitter=lambda ceiling: ceiling / 2,
                sleeper=virtual_sleep,
                max_attempts=3,
            )
            with pytest.raises(RecoveryError) as caught:
                await gateway.complete_with_recovery(**args)
        assert requests == []
        assert isinstance(caught.value.inspect_cause(), ValueError)
        assert caught.value.report.history == ()


class DescribeAnthropicCapabilityBoundary:
    async def should_reject_unsupported_configured_json_format_before_dispatch(self):
        with scripted_http([(200, {}, success("anthropic"))]) as (host, requests):
            gateway = cloud_gateway(
                host,
                "anthropic",
                RecoveryPolicy(
                    monotonic=clock,
                    wall=lambda: 0,
                    jitter=lambda ceiling: ceiling / 2,
                    sleeper=virtual_sleep,
                    max_attempts=3,
                ),
            )
            with pytest.raises(RecoveryError) as caught:
                await gateway.complete_with_recovery(
                    model="claude-test",
                    messages=[LLMMessage(content="héllo")],
                    config=CompletionConfig(
                        response_format=ResponseFormat(type="json_object")
                    ),
                )
        assert requests == []
        assert isinstance(caught.value.inspect_cause(), NotImplementedError)
        assert caught.value.report.history == ()

    @pytest.mark.parametrize("entrypoint", ["generate", "generate_response", "send"])
    def should_recover_ordinary_completion_through_public_callers(
        self, entrypoint, broker_factory
    ):
        with scripted_http(
            [(503, {}, b"private"), (200, {}, success("anthropic"))]
        ) as (host, requests):
            broker = broker_factory(
                cloud_gateway(
                    host,
                    "anthropic",
                    RecoveryPolicy(
                        monotonic=clock,
                        wall=lambda: 0,
                        jitter=lambda ceiling: ceiling / 2,
                        sleeper=virtual_sleep,
                        max_attempts=2,
                        base_delay=0,
                    ),
                )
            )
            session = ChatSession(broker, tokenizer_gateway=broker.tokenizer)
            messages = [LLMMessage(content="payload")]
            result = {
                "generate": lambda: broker.generate(messages),
                "generate_response": lambda: broker.generate_response(messages).content,
                "send": lambda: session.send("payload"),
            }[entrypoint]()
        assert result == "answer"
        assert len(requests) == 2
        assert requests[0][1] == requests[1][1]
        assert all(path == "/v1/messages" for path, body, headers in requests)

    @pytest.mark.parametrize("operation", ["tools"])
    async def should_reject_unsupported_recovery_before_dispatch(
        self, operation, counter_tool
    ):
        with scripted_http([]) as (host, requests):
            gateway = cloud_gateway(
                host,
                "anthropic",
                RecoveryPolicy(
                    monotonic=clock,
                    wall=lambda: 0,
                    jitter=lambda ceiling: ceiling / 2,
                    sleeper=virtual_sleep,
                    max_attempts=3,
                ),
            )
            args = {"model": "claude-test", "messages": [LLMMessage(content="private")]}
            args |= {
                "tools": {"tools": [counter_tool]},
                "streaming": {},
            }[operation]
            with pytest.raises(RecoveryError) as caught:
                await gateway.complete_with_recovery(**args)
            assert isinstance(caught.value.inspect_cause(), NotImplementedError)
            assert caught.value.report.history == ()
        assert requests == []
        capabilities = gateway.recovery_capabilities()
        assert capabilities.ordinary_recovery
        assert capabilities.structured_recovery
        assert not capabilities.streaming_recovery
        assert not hasattr(gateway, "complete_stream")
        assert not hasattr(gateway, "complete_stream_with_recovery")
        assert capabilities.remote_cancellation == "unsupported"
        assert capabilities.inference_termination == "unknown"


class DescribeCloudRecovery:
    def should_observe_content_before_failing_capture_without_delivery_or_replay(self):
        body = b'data: {"choices":[{"index":0,"delta":{"content":"secret"}}]}\n\ndata: [DONE]\n\n'
        cause = OSError("secret capture failure")
        lifecycle = []

        def capture(event):
            if event.kind == "body":
                raise cause

        with scripted_http([(200, {"Content-Type": "text/event-stream"}, body)]) as (
            host,
            requests,
        ):
            gateway = OpenAIGateway(api_key="private-key", base_url=host)
            gateway.recovery_policy = RecoveryPolicy(
                monotonic=clock,
                wall=lambda: 0,
                jitter=lambda ceiling: ceiling / 2,
                sleeper=virtual_sleep,
                max_attempts=3,
                wire_observer=capture,
                observer=lifecycle.append,
            )
            gateway.recovery_call = None
            delivered = []
            with pytest.raises(RecoveryError) as caught:
                delivered.extend(
                    gateway.complete_stream(
                        model="gpt-4o",
                        messages=[LLMMessage(content="héllo")],
                        config=CompletionConfig(temperature=1.0, max_tokens=16384),
                    )
                )

        failure = caught.value.report.final_failure
        assert delivered == []
        assert len(requests) == 1
        assert requests[0][1] == (
            b'{"model":"gpt-4o","messages":[{"role":"user","content":"h\xc3\xa9llo"}],'
            b'"temperature":1.0,"max_tokens":16384,"stream":true,"stream_options":{"include_usage":true}}'
        )
        assert failure.provider == "openai"
        assert failure.progress.observed_content
        assert failure.progress.delivered_content == 0
        assert failure.reason == "capture_failed"
        assert failure.inspect_cause().inspect_cause() is cause
        assert failure.inspect_response() == body
        assert [event.transition for event in lifecycle] == [
            "attempt_started",
            "attempt_failed",
            "interrupted",
        ]
