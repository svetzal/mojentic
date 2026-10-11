"""HTTP 429 conformance through public oMLX recovery entrypoints."""

import httpx
import pytest

from mojentic.llm.gateways.models import LLMMessage
from mojentic.llm.gateways.ollama_recovery_spec import scripted_http
from mojentic.llm.gateways.omlx import OMLXGateway
from mojentic.llm.gateways.omlx_recovery_spec import Result, allow, completion, reject, stream
from mojentic.llm.recovery import RecoveryError, RecoveryPolicy


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
        events = [event async for event in gateway.complete_stream_with_recovery(**args)]
        if events[-1].error is not None:
            raise events[-1].error
        assert events[-1].kind == "completed"
        return events[-1].response
    return await gateway.complete_with_recovery(
        **args, object_model=Result if operation == "structured" else None
    )


class DescribeOMLX429Recovery:
    async def should_recover_429_only_after_admission_with_exact_wire_evidence(self):
        operation = "streaming"
        lifecycle, captures, delays, admissions = [], [], [], []

        async def sleep(value):
            delays.append(value)

        async def admit(context):
            admissions.append(context)
            return await reject(context)

        with scripted_http(
            [(429, {"Retry-After": "Thu, 01 Jan 1970 00:00:03 GMT"}, b"busy-429"), (200, {}, stream("é"))]
        ) as (host, requests):
            gateway = OMLXGateway(
                host=host,
                recovery_policy=RecoveryPolicy(
                    max_attempts=2, base_delay=1, jitter=lambda ceiling: 0.5,
                    wall=lambda: 0, monotonic=lambda: 0, sleeper=sleep,
                    admission=admit, observer=lifecycle.append, wire_observer=captures.append,
                ),
            )
            try:
                response = await request(gateway, operation)
            except RecoveryError as error:
                assert error.report.outcome == "admission_rejected"
                assert error.report.final_failure.http_status == 429
                assert error.report.final_failure.retry_after.delay == 3
                assert [(path, body) for path, body, headers in requests] == [
                    ("/v1/chat/completions", EXPECTED[operation])
                ]
                assert [event.transition for event in lifecycle] == [
                    "attempt_started", "attempt_failed", "admission_pending", "admission_rejected", "exhausted"
                ]
                raise
            assert [(path, body) for path, body, headers in requests] == [
                ("/v1/chat/completions", EXPECTED[operation]),
                ("/v1/chat/completions", EXPECTED[operation]),
            ]
        assert response.content == "é"
        assert delays == [3]
        report = response.recovery_report
        assert report.outcome == "succeeded"
        assert len(report.history) == 1
        failure = report.history[0]
        assert failure.http_status == 429
        assert failure.retry_after.state == "date"
        assert failure.retry_after.delay == 3
        assert failure.provider == "omlx"
        assert failure.operation == operation
        assert failure.eligible
        cause = failure.inspect_cause()
        assert isinstance(cause, httpx.HTTPStatusError)
        assert cause.response.status_code == 429
        assert cause.request.content == EXPECTED[operation]
        assert failure.inspect_response() == b"busy-429"
        assert admissions[0].failure is failure
        assert report.identity.wire_attempt == 2
        assert failure.identity.wire_attempt == 1
        assert failure.identity.logical_request_id == report.identity.logical_request_id
        assert failure.identity.attempt_id != report.identity.attempt_id
        sends = [event for event in captures if event.kind == "request"]
        assert [event.body for event in sends] == [EXPECTED[operation], EXPECTED[operation]]
        assert [event.identity for event in sends] == [failure.identity, report.identity]
        assert [event.transition for event in lifecycle] == [
            "attempt_started", "attempt_failed", "admission_pending", "admission_allowed",
            "delay_scheduled", "retry_started", "attempt_started", "attempt_succeeded",
        ]
