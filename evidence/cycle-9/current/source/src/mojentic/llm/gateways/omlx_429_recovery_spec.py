"""HTTP 429 conformance through public oMLX recovery entrypoints."""

import httpx
import pytest

from mojentic.llm.gateways.models import LLMMessage
from mojentic.llm.gateways.ollama_recovery_spec import scripted_http
from mojentic.llm.gateways.omlx import OMLXGateway
from mojentic.llm.gateways.omlx_recovery_spec import (
    Result,
    allow,
    completion,
    reject,
    stream,
)
from mojentic.llm.recovery import RecoveryError, RecoveryPolicy
from mojentic.llm.recovery_stream import StreamOutcome

EXPECTED = {
    "ordinary": b'{"model":"test","messages":[{"role":"user","content":"h\xc3\xa9llo"}],"temperature":1.0,"max_tokens":16384}',
    "structured": (
        b'{"model":"test","messages":[{"role":"user","content":"h\xc3\xa9llo"}],"temperature":1.0,"max_tokens":16384,'
        b'"response_format":{"type":"json_schema","json_schema":{"name":"response","schema":'
        b'{"properties":{"answer":{"title":"Answer","type":"string"}},"required":["answer"],'
        b'"title":"Result","type":"object"}}}}'
    ),
    "streaming": (
        b'{"model":"test","messages":[{"role":"user","content":"h\xc3\xa9llo"}],"temperature":1.0,"max_tokens":16384,'
        b'"stream":true,"stream_options":{"include_usage":true}}'
    ),
}


async def request(gateway, operation):
    args = {"model": "test", "messages": [LLMMessage(content="héllo")]}
    if operation == "streaming":
        events = [
            event async for event in gateway.complete_stream_with_recovery(**args)
        ]
        terminal = events[-1]
        if terminal.error is not None:
            assert [event.kind for event in events] == ["failed"]
            assert terminal.response is None
            assert isinstance(terminal.outcome, StreamOutcome)
            assert terminal.outcome.value == terminal.error.report.outcome
            assert terminal.identity == terminal.error.report.identity
            raise terminal.error
        assert terminal.kind == "completed"
        assert terminal.outcome is StreamOutcome.SUCCEEDED
        assert terminal.identity == terminal.response.recovery_report.identity
        return terminal.response
    return await gateway.complete_with_recovery(
        **args, object_model=Result if operation == "structured" else None
    )


OPERATIONS = ["ordinary", "structured", "streaming"]
SUCCESS = {
    "ordinary": completion("é"),
    "structured": completion('{"answer":"é"}'),
    "streaming": stream("é"),
}
CONTENT = {"ordinary": "é", "structured": '{"answer":"é"}', "streaming": "é"}
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


def assert_failure(failure, operation, state, minimum):
    assert failure.http_status == 429
    assert failure.retry_after.state == state
    assert failure.retry_after.delay == minimum
    assert failure.provider == "omlx"
    assert failure.operation == operation
    assert failure.category == "http"
    assert failure.eligible
    assert not failure.progress.semantic
    cause = failure.inspect_cause()
    assert isinstance(cause, httpx.HTTPStatusError)
    assert cause.response.status_code == 429
    assert cause.request.content == EXPECTED[operation]
    assert failure.inspect_response() == b"busy-429"
    assert failure.identity.wire_attempt == 1
    assert failure.identity.logical_request_id
    assert failure.identity.attempt_id


class DescribeOMLX429Recovery:
    @pytest.mark.parametrize("operation", OPERATIONS)
    @pytest.mark.parametrize(
        "headers,state,minimum,jitter,delay",
        [
            ({"Retry-After": "2"}, "seconds", 2, 0.5, 2),
            ({"Retry-After": "1"}, "seconds", 1, 2, 2),
            ({"Retry-After": "Thu, 01 Jan 1970 00:00:03 GMT"}, "date", 3, 0.5, 3),
            ({"Retry-After": "Thu, 01 Jan 1970 00:00:01 GMT"}, "date", 1, 2, 2),
            ({"Retry-After": "Wed, 31 Dec 1969 23:59:59 GMT"}, "date", 0, 0.5, 0.5),
            ({"Retry-After": "invalid"}, "invalid", None, 0.5, 0.5),
            ({}, "absent", None, 0.5, 0.5),
        ],
        ids=[
            "seconds-minimum",
            "seconds-jitter",
            "date-minimum",
            "date-jitter",
            "past-date",
            "invalid",
            "absent",
        ],
    )
    async def should_recover_429_only_after_admission_with_exact_wire_evidence(
        self, operation, headers, state, minimum, jitter, delay
    ):
        lifecycle, captures, delays, admissions, jitter_ceilings = [], [], [], [], []

        async def sleep(value):
            delays.append(value)

        def choose_jitter(ceiling):
            jitter_ceilings.append(ceiling)
            return jitter

        async def admit(context):
            admissions.append(context)
            return await allow(context)

        with scripted_http(
            [(429, headers, b"busy-429"), (200, {}, SUCCESS[operation])]
        ) as (host, requests):
            gateway = OMLXGateway(
                host=host,
                recovery_policy=RecoveryPolicy(
                    max_attempts=2,
                    base_delay=4,
                    jitter=choose_jitter,
                    wall=lambda: 0,
                    monotonic=lambda: 0,
                    sleeper=sleep,
                    admission=admit,
                    observer=lifecycle.append,
                    wire_observer=captures.append,
                ),
            )
            response = await request(gateway, operation)
            assert [(path, body) for path, body, headers in requests] == [
                ("/v1/chat/completions", EXPECTED[operation]),
                ("/v1/chat/completions", EXPECTED[operation]),
            ]
        assert response.content == CONTENT[operation]
        assert (
            response.object
            == {"ordinary": None, "structured": Result(answer="é"), "streaming": None}[
                operation
            ]
        )
        assert response.model == "actual-model"
        assert response.usage == {
            "prompt_tokens": 2,
            "completion_tokens": 3,
            "total_tokens": 5,
        }
        assert (
            response.finish_reason
            == {"ordinary": "length", "structured": "length", "streaming": "stop"}[
                operation
            ]
        )
        assert delays == [delay]
        assert jitter_ceilings == [4]
        report = response.recovery_report
        assert report.outcome == "succeeded"
        assert report.final_failure is None
        assert len(report.history) == 1
        failure = report.history[0]
        assert_failure(failure, operation, state, minimum)
        assert admissions[0].failure is failure
        assert len(admissions) == 1
        assert admissions[0].previous_identity == failure.identity
        assert admissions[0].next_attempt == 2
        assert report.identity.wire_attempt == 2
        assert failure.identity.logical_request_id == report.identity.logical_request_id
        assert failure.identity.attempt_id != report.identity.attempt_id
        sends = [event for event in captures if event.kind == "request"]
        assert [event.body for event in sends] == [
            EXPECTED[operation],
            EXPECTED[operation],
        ]
        assert [event.identity for event in sends] == [
            failure.identity,
            report.identity,
        ]
        assert [event.status for event in captures if event.kind == "headers"] == [
            429,
            200,
        ]
        assert [event.transition for event in lifecycle] == RECOVERED
        assert [event.identity for event in lifecycle] == [failure.identity] * 6 + [
            report.identity
        ] * 2
        assert lifecycle[1].failure is failure
        assert lifecycle[4].delay == delay

    @pytest.mark.parametrize("operation", OPERATIONS)
    @pytest.mark.parametrize(
        "policy_args,elapsed_before,elapsed_after,outcome,transitions,admission_count",
        [
            ({"delay_ceiling": 1}, 0, 0, "delay_ceiling", [], 0),
            ({"budget": 1}, 0, 0, "budget_exhausted", [], 0),
            ({"budget": 4}, 3, 0, "budget_exhausted", [], 0),
            (
                {"budget": 4},
                0,
                3,
                "budget_exhausted",
                ["admission_pending", "admission_allowed"],
                1,
            ),
        ],
        ids=[
            "delay-ceiling",
            "budget",
            "remaining-before-admission",
            "remaining-after-admission",
        ],
    )
    async def should_refuse_429_minimum_outside_limits_without_another_send(
        self,
        operation,
        policy_args,
        elapsed_before,
        elapsed_after,
        outcome,
        transitions,
        admission_count,
    ):
        lifecycle, captures, delays, admissions = [], [], [], []
        clock = [0]

        def observe(event):
            lifecycle.append(event)
            if event.transition == "attempt_failed":
                clock[0] = elapsed_before

        async def sleep(value):
            delays.append(value)

        async def admit(context):
            admissions.append(context)
            clock[0] += elapsed_after
            return await allow(context)

        with scripted_http([(429, {"Retry-After": "2"}, b"busy-429")]) as (
            host,
            requests,
        ):
            gateway = OMLXGateway(
                host=host,
                recovery_policy=RecoveryPolicy(
                    max_attempts=2,
                    base_delay=0,
                    jitter=lambda ceiling: 0,
                    wall=lambda: 0,
                    monotonic=lambda: clock[0],
                    sleeper=sleep,
                    admission=admit,
                    observer=observe,
                    wire_observer=captures.append,
                    **policy_args,
                ),
            )
            with pytest.raises(RecoveryError) as caught:
                await request(gateway, operation)
            assert [(path, body) for path, body, headers in requests] == [
                ("/v1/chat/completions", EXPECTED[operation])
            ]
        report = caught.value.report
        assert report.outcome == outcome
        failure = report.final_failure
        assert report.history == (failure,)
        assert_failure(failure, operation, "seconds", 2)
        assert caught.value.inspect_cause(0) is failure.inspect_cause()
        assert caught.value.inspect_response(0) == b"busy-429"
        assert report.identity == failure.identity
        assert not report.progress.semantic
        assert delays == []
        assert len(admissions) == admission_count
        assert [event.transition for event in lifecycle] == [
            "attempt_started",
            "attempt_failed",
            *transitions,
            "exhausted",
        ]
        assert [event.identity for event in lifecycle] == [failure.identity] * len(
            lifecycle
        )
        sends = [event for event in captures if event.kind == "request"]
        assert [event.body for event in sends] == [EXPECTED[operation]]
        assert [event.identity for event in sends] == [failure.identity]
        assert [event.status for event in captures if event.kind == "headers"] == [429]

    @pytest.mark.parametrize("operation", OPERATIONS)
    @pytest.mark.parametrize(
        "admission,outcome,transitions",
        [
            (None, "admission_required", ["admission_required"]),
            (reject, "admission_rejected", ["admission_pending", "admission_rejected"]),
        ],
        ids=["required", "rejected"],
    )
    async def should_refuse_eligible_429_without_admission(
        self, operation, admission, outcome, transitions
    ):
        lifecycle, captures, delays = [], [], []

        async def sleep(value):
            delays.append(value)

        with scripted_http([(429, {"Retry-After": "2"}, b"busy-429")]) as (
            host,
            requests,
        ):
            gateway = OMLXGateway(
                host=host,
                recovery_policy=RecoveryPolicy(
                    max_attempts=2,
                    base_delay=0,
                    wall=lambda: 0,
                    monotonic=lambda: 0,
                    admission=admission,
                    sleeper=sleep,
                    observer=lifecycle.append,
                    wire_observer=captures.append,
                ),
            )
            with pytest.raises(RecoveryError) as caught:
                await request(gateway, operation)
            assert [(path, body) for path, body, headers in requests] == [
                ("/v1/chat/completions", EXPECTED[operation])
            ]
        report = caught.value.report
        assert report.outcome == outcome
        failure = report.final_failure
        assert report.history == (failure,)
        assert_failure(failure, operation, "seconds", 2)
        assert caught.value.inspect_cause(0) is failure.inspect_cause()
        assert caught.value.inspect_response(0) == b"busy-429"
        assert report.identity == failure.identity
        assert not report.progress.semantic
        assert delays == []
        assert [event.transition for event in lifecycle] == [
            "attempt_started",
            "attempt_failed",
            *transitions,
            "exhausted",
        ]
        sends = [event for event in captures if event.kind == "request"]
        assert [event.body for event in sends] == [EXPECTED[operation]]
        assert [event.identity for event in sends] == [failure.identity]
