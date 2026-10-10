"""Recovery specifications exercise actual loopback HTTP through public callers."""

import asyncio
import base64
import json
import os
import threading
import time
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

from mojentic.llm.gateways.models import LLMMessage, MessageRole
from mojentic.llm.gateways.ollama import OllamaGateway
from mojentic.llm.llm_broker import LLMBroker


@contextmanager
def scripted_http(replies):
    requests = []

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            body = self.rfile.read(int(self.headers["Content-Length"]))
            requests.append((self.path, body, dict(self.headers)))
            status, headers, data = replies[len(requests) - 1]
            delay = 0
            if isinstance(data, tuple):
                delay, data = data
            self.send_response(status)
            for key, value in headers.items():
                self.send_header(key, value)
            if "Content-Length" not in headers:
                self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            time.sleep(delay)
            try:
                self.wfile.write(data)
            except (BrokenPipeError, ConnectionResetError):
                pass
            self.close_connection = True

        def log_message(self, *args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(
        target=lambda: server.serve_forever(poll_interval=0.01), daemon=True
    )
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}", requests
    finally:
        server.shutdown()
        server.server_close()
        thread.join()
        if os.environ.get("MOJENTIC_RECOVERY_EVIDENCE") == "1":
            evidence = {
                "test": os.environ.get("PYTEST_CURRENT_TEST"),
                "endpoint": f"http://127.0.0.1:{server.server_port}",
                "received_requests": [
                    {
                        "path": path,
                        "body_base64": base64.b64encode(body).decode(),
                        "headers": headers,
                    }
                    for path, body, headers in requests
                ],
            }
            with Path(".foundry/logs/loopback.jsonl").open("a") as log:
                log.write(json.dumps(evidence) + "\n")


def frame(content="answer", **message):
    return json.dumps(
        {
            "model": "test",
            "done": True,
            "done_reason": "stop",
            "message": {"role": "assistant", "content": content, **message},
        }
    ).encode()


def retain_wire_evidence(captured):
    if os.environ.get("MOJENTIC_RECOVERY_EVIDENCE") == "1":
        with Path(".foundry/logs/authenticated_capture.jsonl").open("a") as log:
            for event in captured:
                evidence = event.model_dump(exclude={"body"})
                evidence["body_base64"] = base64.b64encode(event.body).decode()
                evidence["test"] = os.environ.get("PYTEST_CURRENT_TEST")
                log.write(json.dumps(evidence) + "\n")


class DescribeLintValidationBoundary:
    def should_propagate_validator_programming_errors_after_one_wire_request(self):
        from pydantic import BaseModel, field_validator

        class Result(BaseModel):
            answer: str

            @field_validator("answer")
            @classmethod
            def validate_answer(cls, value):
                raise TypeError("validator programming defect")

        with scripted_http([(200, {}, frame('{"answer":"ok"}'))]) as (host, requests):
            gateway = OllamaGateway(host=host)

            with pytest.raises(TypeError, match="validator programming defect"):
                gateway.complete(model="test", messages=[], object_model=Result)

            assert len(requests) == 1
            payload = json.loads(requests[0][1])
            assert payload["format"] == Result.model_json_schema()
            assert payload["stream"] is False


class DescribeHttpBoundaryCorrection:
    def should_keep_predispatch_expiry_observer_failure_private(self, messages):
        from mojentic.llm.recovery import RecoveryError, RecoveryPolicy

        cause = OSError("secret-observer")

        def observe(event):
            raise cause

        with scripted_http([]) as (host, requests):
            gateway = OllamaGateway(
                host=host,
                recovery_policy=RecoveryPolicy(
                    deadline=0,
                    monotonic=lambda: 1,
                    observer=observe,
                ),
            )
            with pytest.raises(RecoveryError) as caught:
                gateway.complete(model="test", messages=messages)

        assert requests == []
        assert caught.value.report.identity.wire_attempt == 0
        assert caught.value.report.history == ()
        assert caught.value.report.outcome == "interrupted"
        assert caught.value.inspect_cause() is cause
        assert caught.value.report.final_failure.inspect_cause() is cause
        assert "secret" not in str(caught.value) + caught.value.report.model_dump_json()

    @pytest.mark.parametrize(
        "entrypoint",
        ["gateway", "generate", "generate_response", "generate_object", "session"],
    )
    def should_capture_the_authenticated_request_actually_sent(
        self, messages, broker_factory, entrypoint
    ):
        from pydantic import BaseModel

        from mojentic.llm.chat_session import ChatSession
        from mojentic.llm.recovery import RecoveryPolicy

        class Answer(BaseModel):
            value: str

        captured, events = [], []
        with scripted_http(
            [(503, {}, b"private"), (200, {}, frame('{"value":"answer"}'))]
        ) as (host, requests):
            gateway = OllamaGateway(
                host=host.replace("http://", "http://username:password@"),
                recovery_policy=RecoveryPolicy(
                    max_attempts=2,
                    base_delay=0,
                    admission=allow,
                    wire_observer=captured.append,
                    observer=events.append,
                ),
            )
            broker = broker_factory(gateway)
            operations = {
                "gateway": lambda: gateway.complete(model="test", messages=messages),
                "generate": lambda: broker.generate(messages),
                "generate_response": lambda: broker.generate_response(messages),
                "generate_object": lambda: broker.generate_object(messages, Answer),
                "session": lambda: ChatSession(broker).send("payload-sentinel"),
            }
            operations[entrypoint]()

        outgoing = [event for event in captured if event.kind == "request"]
        assert len(requests) == len(outgoing) == 2
        assert outgoing[0].body == outgoing[1].body == requests[0][1] == requests[1][1]
        for request, received in zip(outgoing, requests, strict=True):
            assert (
                dict(request.headers)["authorization"] == received[2]["Authorization"]
            )
            assert received[2]["Authorization"] == "Basic dXNlcm5hbWU6cGFzc3dvcmQ="
            assert request.url.endswith(received[0])
        assert (
            outgoing[0].identity.logical_request_id
            == outgoing[1].identity.logical_request_id
        )
        assert outgoing[0].identity.attempt_id != outgoing[1].identity.attempt_id
        assert outgoing[0].identity.attempt_id is not None
        assert outgoing[1].identity.attempt_id is not None
        assert [event.identity.wire_attempt for event in outgoing] == [1, 2]
        retain_wire_evidence(captured)

    @pytest.mark.parametrize(
        "stage", ["request", "attempt_started", "headers", "body", "attempt_succeeded"]
    )
    async def should_make_callback_cancellation_authoritative(self, messages, stage):
        from mojentic.llm.recovery import RecoveryCall, RecoveryError, RecoveryPolicy

        call, events, captured = RecoveryCall(), [], []

        def capture(event):
            captured.append(event)
            if event.kind == stage:
                call.cancel()

        def observe(event):
            events.append(event)
            if event.transition == stage:
                call.cancel()

        body = frame("secret-content", thinking="secret-reasoning")
        with scripted_http([(200, {"X-Private": "secret-header"}, body)]) as (
            host,
            requests,
        ):
            gateway = OllamaGateway(
                host=host,
                recovery_policy=RecoveryPolicy(
                    max_attempts=3,
                    admission=allow,
                    wire_observer=capture,
                    observer=observe,
                ),
            )
            with pytest.raises(RecoveryError) as caught:
                await gateway.complete_with_recovery(
                    call=call, model="test", messages=messages
                )

        error = caught.value
        failure = error.report.final_failure
        expected_count = {
            "request": 0,
            "attempt_started": 0,
            "headers": 1,
            "body": 1,
            "attempt_succeeded": 1,
        }[stage]
        assert len(requests) == error.report.identity.wire_attempt == expected_count
        assert len(error.report.history) == expected_count
        assert error.report.outcome == "cancelled"
        assert failure.category == "cancellation"
        assert isinstance(error.inspect_cause(), asyncio.CancelledError)
        assert isinstance(failure.inspect_cause(), asyncio.CancelledError)
        assert (
            failure.progress.delivered_content
            == failure.progress.delivered_reasoning
            == 0
        )
        assert [event.transition for event in events].count("cancelled") == 1
        assert events[-1].transition == "cancelled"
        assert [event.transition for event in events].count(
            "attempt_failed"
        ) == expected_count
        assert failure.http_status == {0: None, 1: 200}[expected_count]
        assert (
            dict(failure.inspect_headers()).get("x-private")
            == {0: None, 1: "secret-header"}[expected_count]
        )
        assert error.inspect_headers() == failure.inspect_headers()
        assert error.report.history == {0: (), 1: (failure,)}[expected_count]
        assert (error.report.identity.attempt_id is not None) == bool(expected_count)
        expected_body = {
            "request": b"",
            "attempt_started": b"",
            "headers": b"",
            "body": body,
            "attempt_succeeded": body,
        }[stage]
        assert (
            failure.progress.observed_content
            == failure.progress.observed_reasoning
            == bool(expected_body)
        )
        assert failure.progress.raw_bytes == len(expected_body)
        assert failure.inspect_response() == expected_body
        assert (
            "secret" not in str(error) + repr(failure) + error.report.model_dump_json()
        )

    @pytest.mark.parametrize(
        "stage",
        [
            "admission_allowed",
            "delay_scheduled",
            "retry_started",
            "request",
            "attempt_started",
        ],
    )
    def should_refuse_callback_expiry_without_phantom_retry(self, messages, stage):
        from mojentic.llm.recovery import RecoveryError, RecoveryPolicy

        now, events = [10.0], []

        def capture(event):
            if event.kind == stage and event.identity.wire_attempt == 2:
                now[0] = 12.0

        def observe(event):
            events.append(event)
            if event.transition == stage and (
                stage != "attempt_started" or event.identity.wire_attempt == 2
            ):
                now[0] = 12.0

        with scripted_http([(503, {}, b"private"), (200, {}, frame())]) as (
            host,
            requests,
        ):
            gateway = OllamaGateway(
                host=host,
                recovery_policy=RecoveryPolicy(
                    max_attempts=2,
                    base_delay=0,
                    admission=allow,
                    deadline=11,
                    monotonic=lambda: now[0],
                    wire_observer=capture,
                    observer=observe,
                ),
            )
            with pytest.raises(RecoveryError) as caught:
                gateway.complete(model="test", messages=messages)

        assert len(requests) == caught.value.report.identity.wire_attempt == 1
        assert len(caught.value.report.history) == 1
        assert caught.value.report.outcome == "budget_exhausted"
        assert [event.transition for event in events].count("exhausted") == 1
        assert "attempt_succeeded" not in [event.transition for event in events]

    @pytest.mark.parametrize("echo_source", ["credentials", "payload"])
    def should_keep_uuid_shaped_secret_echoes_private(self, messages, echo_source):
        from mojentic.llm.recovery import RecoveryError, RecoveryPolicy

        secret = "bd38be36-6698-43f1-9d34-7452b980f471"
        events, captured = [], []
        messages[0].content = secret if echo_source == "payload" else "payload-sentinel"
        with scripted_http(
            [(503, {"X-Request-ID": secret, "X-Echo": secret}, secret.encode())]
        ) as (host, requests):
            host = (
                host.replace("http://", f"http://{secret}:password@")
                if echo_source == "credentials"
                else host
            )
            gateway = OllamaGateway(
                host=host,
                recovery_policy=RecoveryPolicy(
                    wire_observer=captured.append,
                    observer=events.append,
                ),
            )
            with pytest.raises(RecoveryError) as caught:
                gateway.complete(model="test", messages=messages)

        failure = caught.value.report.final_failure
        assert len(requests) == 1
        assert failure.provider_request_id is None
        assert dict(failure.inspect_headers())["x-request-id"] == secret
        assert failure.inspect_response() == secret.encode()
        assert captured[-1].body == secret.encode()
        safe = (
            str(caught.value)
            + repr(caught.value)
            + repr(failure)
            + caught.value.report.model_dump_json()
        )
        safe += "".join(event.model_dump_json() + repr(event) for event in events)
        assert secret not in safe
        retain_wire_evidence(captured)

    @pytest.mark.parametrize(
        "stage",
        [
            "attempt_failed",
            "admission_pending",
            "admission_allowed",
            "delay_scheduled",
            "retry_started",
        ],
    )
    async def should_cancel_at_admission_and_backoff_callbacks_without_resending(
        self, messages, stage
    ):
        from mojentic.llm.recovery import RecoveryCall, RecoveryError, RecoveryPolicy

        call, events = RecoveryCall(), []

        def observe(event):
            events.append(event)
            if event.transition == stage:
                call.cancel()

        with scripted_http([(503, {"X-Private": "secret"}, b"private")]) as (
            host,
            requests,
        ):
            gateway = OllamaGateway(
                host=host,
                recovery_policy=RecoveryPolicy(
                    max_attempts=2,
                    base_delay=0,
                    admission=allow,
                    observer=observe,
                ),
            )
            with pytest.raises(RecoveryError) as caught:
                await gateway.complete_with_recovery(
                    call=call, model="test", messages=messages
                )

        error = caught.value
        assert (
            len(requests)
            == error.report.identity.wire_attempt
            == len(error.report.history)
            == 1
        )
        assert error.report.outcome == "cancelled"
        assert isinstance(error.inspect_cause(), asyncio.CancelledError)
        assert isinstance(
            error.report.final_failure.inspect_cause(), asyncio.CancelledError
        )
        assert error.report.history[0].http_status == 503
        assert dict(error.report.history[0].inspect_headers())["x-private"] == "secret"
        assert [event.transition for event in events].count("attempt_failed") == 1
        assert [event.transition for event in events].count("cancelled") == 1
        assert events[-1].transition == "cancelled"


class DescribePublicRecoveryProof:
    def should_retain_observed_semantics_before_failed_capture_without_replay(
        self, mocker
    ):
        from mojentic.llm.gateways.tokenizer_gateway import TokenizerGateway
        from mojentic.llm.recovery import RecoveryError, RecoveryPolicy

        events = []
        captured = []
        secret = "credential-and-payload-sentinel"
        original = OSError(secret)

        def capture(event):
            captured.append(event)
            if event.kind == "body":
                raise original

        with scripted_http([(200, {}, frame(secret, thinking=secret))]) as (
            host,
            requests,
        ):
            gateway = OllamaGateway(
                host=host,
                recovery_policy=RecoveryPolicy(
                    max_attempts=3, wire_observer=capture, observer=events.append
                ),
            )
            tokenizer = mocker.Mock(spec=TokenizerGateway)
            tokenizer.encode.return_value = []
            broker = LLMBroker("test", gateway=gateway, tokenizer=tokenizer)

            with pytest.raises(RecoveryError) as caught:
                broker.generate_response(
                    [LLMMessage(role=MessageRole.User, content=secret)]
                )

        error = caught.value
        failure = error.report.history[-1]
        assert len(requests) == 1
        assert failure.progress.observed_content and failure.progress.observed_reasoning
        assert failure.progress.delivered_content == 0
        assert error.inspect_cause() is original
        assert error.inspect_response() == frame(secret, thinking=secret)
        assert [event.transition for event in events] == [
            "attempt_started",
            "attempt_failed",
            "interrupted",
        ]
        assert len(error.report.history) == 1
        assert captured[0].body == requests[0][1]
        assert secret not in str(error) + repr(error) + error.report.model_dump_json()
        assert secret not in "".join(event.model_dump_json() for event in events)


async def allow(context):
    return "allow"


async def reject(context):
    return "reject"


@pytest.fixture
def messages():
    return [LLMMessage(role=MessageRole.User, content="payload-sentinel")]


@pytest.fixture
def broker_factory(mocker):
    from mojentic.llm.gateways.tokenizer_gateway import TokenizerGateway

    def create(gateway):
        tokenizer = mocker.Mock(spec=TokenizerGateway)
        tokenizer.encode.return_value = []
        return LLMBroker("test", gateway=gateway, tokenizer=tokenizer)

    return create


class DescribeRecoveryBoundaries:
    @pytest.mark.parametrize(
        "entrypoint", ["generate", "generate_response", "generate_object", "send"]
    )
    def should_recover_admitted_503_with_identical_bytes(
        self, entrypoint, messages, broker_factory
    ):
        from pydantic import BaseModel

        from mojentic.llm.chat_session import ChatSession
        from mojentic.llm.completion_config import CompletionConfig
        from mojentic.llm.recovery import RecoveryPolicy

        class Answer(BaseModel):
            value: int

        events, captured = [], []
        result_frame = frame('{"value": 7}', thinking="native reasoning")
        with scripted_http([(503, {}, b"failure"), (200, {}, result_frame)]) as (
            host,
            requests,
        ):
            gateway = OllamaGateway(
                host=host,
                recovery_policy=RecoveryPolicy(
                    max_attempts=2,
                    base_delay=0,
                    admission=allow,
                    observer=events.append,
                    wire_observer=captured.append,
                ),
            )
            broker = broker_factory(gateway)
            config = CompletionConfig(
                reasoning_effort="high", temperature=0.3, num_ctx=1024, max_tokens=17
            )
            calls = {
                "generate": lambda: broker.generate(messages, config=config),
                "generate_response": lambda: (
                    broker.generate_response(messages, config=config).content
                ),
                "generate_object": lambda: broker.generate_object(
                    messages, Answer, config=config
                ).model_dump_json(),
                "send": lambda: ChatSession(broker, config=config).send(
                    "payload-sentinel"
                ),
            }

            result = calls[entrypoint]()

        assert json.loads(result) == {"value": 7}
        assert len(requests) == 2
        assert requests[0][0] == requests[1][0] == "/api/chat"
        assert requests[0][1] == requests[1][1]
        request = json.loads(requests[0][1])
        assert request["think"] is True
        assert request["options"] == {
            "temperature": 0.3,
            "num_ctx": 1024,
            "num_predict": 17,
        }
        assert request["stream"] is False
        assert [event.transition for event in events] == [
            "attempt_started",
            "attempt_failed",
            "admission_pending",
            "admission_allowed",
            "delay_scheduled",
            "retry_started",
            "attempt_started",
            "attempt_succeeded",
        ]
        starts = [
            event.identity for event in events if event.transition == "attempt_started"
        ]
        assert starts[0].logical_request_id == starts[1].logical_request_id
        assert starts[0].attempt_id != starts[1].attempt_id
        assert [identity.wire_attempt for identity in starts] == [1, 2]
        assert len(starts[0].attempt_id) == len(starts[1].attempt_id) == 36
        assert [event.body for event in captured if event.kind == "request"] == [
            requests[0][1],
            requests[1][1],
        ]
        assert (
            b"".join(event.body for event in captured if event.kind == "body")
            == b"failure" + result_frame
        )
        assert [event.status for event in captured if event.kind == "headers"] == [
            503,
            200,
        ]

    def should_exhaust_504_with_complete_typed_history_and_private_echoes(
        self, messages, broker_factory
    ):
        import httpx

        from mojentic.llm.recovery import RecoveryError, RecoveryPolicy

        secret = b"credential-and-payload-sentinel"
        events = []
        with scripted_http([(504, {}, secret)] * 3) as (host, requests):
            broker = broker_factory(
                OllamaGateway(
                    host=host,
                    headers={"Authorization": secret.decode()},
                    recovery_policy=RecoveryPolicy(
                        max_attempts=3,
                        base_delay=0,
                        admission=allow,
                        observer=events.append,
                    ),
                )
            )

            with pytest.raises(RecoveryError) as caught:
                broker.generate(messages)

        error = caught.value
        assert len(requests) == 3
        assert error.report.outcome == "attempts_exhausted"
        assert [failure.identity.wire_attempt for failure in error.report.history] == [
            1,
            2,
            3,
        ]
        assert [failure.http_status for failure in error.report.history] == [
            504,
            504,
            504,
        ]
        assert (
            len({failure.identity.attempt_id for failure in error.report.history}) == 3
        )
        assert (
            len(
                {
                    failure.identity.logical_request_id
                    for failure in error.report.history
                }
            )
            == 1
        )
        assert all(
            isinstance(error.inspect_cause(i), httpx.HTTPStatusError) for i in range(3)
        )
        assert [error.inspect_response(i) for i in range(3)] == [secret] * 3
        assert (
            secret.decode()
            not in str(error) + repr(error) + error.report.model_dump_json()
        )
        assert secret.decode() not in "".join(
            event.model_dump_json() for event in events
        )
        assert [event.transition for event in events] == [
            "attempt_started",
            "attempt_failed",
            "admission_pending",
            "admission_allowed",
            "delay_scheduled",
            "retry_started",
            "attempt_started",
            "attempt_failed",
            "admission_pending",
            "admission_allowed",
            "delay_scheduled",
            "retry_started",
            "attempt_started",
            "attempt_failed",
            "exhausted",
        ]

    @pytest.mark.parametrize("status", [400, 401, 403])
    @pytest.mark.parametrize("truncated", [False, True])
    def should_never_replay_permanent_status_even_when_body_transport_fails(
        self, status, truncated, messages
    ):
        import httpx

        from mojentic.llm.recovery import RecoveryError, RecoveryPolicy

        headers = {"Content-Length": "99"} if truncated else {}
        with scripted_http([(status, headers, b"secret echo")]) as (host, requests):
            gateway = OllamaGateway(
                host=host,
                recovery_policy=RecoveryPolicy(
                    max_attempts=3,
                    retryable_statuses=frozenset({status}),
                    admission=allow,
                ),
            )

            with pytest.raises(RecoveryError) as caught:
                gateway.complete(model="test", messages=messages)

        assert len(requests) == 1
        failure = caught.value.report.final_failure
        assert failure.http_status == status
        assert failure.reason == "permanent"
        assert not failure.eligible
        expected_cause = (
            httpx.RemoteProtocolError if truncated else httpx.HTTPStatusError
        )
        assert isinstance(caught.value.inspect_cause(), expected_cause)
        assert caught.value.inspect_response() == b"secret echo"

    @pytest.mark.parametrize(
        "data",
        [
            b"",
            b"{",
            b"[]",
            b"{}",
            b'{"error":"secret"}',
            b'{"message":{"role":"assistant","content":42}}',
        ],
    )
    def should_reject_malformed_provider_responses_without_replay(self, data, messages):
        from mojentic.llm.recovery import RecoveryError, RecoveryPolicy

        with scripted_http([(200, {}, data)]) as (host, requests):
            gateway = OllamaGateway(
                host=host,
                recovery_policy=RecoveryPolicy(
                    max_attempts=3,
                    admission=allow,
                    retryable_categories=frozenset({"protocol", "provider_response"}),
                ),
            )

            with pytest.raises(RecoveryError) as caught:
                gateway.complete(model="test", messages=messages)

        assert len(requests) == 1
        assert not caught.value.report.final_failure.eligible
        assert isinstance(caught.value.inspect_cause(), (ValueError, TypeError))
        assert caught.value.inspect_response() == data

    def should_preserve_structured_validation_cause(self, messages, broker_factory):
        from pydantic import BaseModel, ValidationError

        from mojentic.llm.recovery import RecoveryError, RecoveryPolicy

        class Answer(BaseModel):
            value: int

        with scripted_http([(200, {}, frame('{"value":"secret"}'))]) as (
            host,
            requests,
        ):
            broker = broker_factory(
                OllamaGateway(host=host, recovery_policy=RecoveryPolicy(max_attempts=3))
            )

            with pytest.raises(RecoveryError) as caught:
                broker.generate_object(messages, Answer)

        assert len(requests) == 1
        assert isinstance(caught.value.inspect_cause(), ValidationError)
        assert caught.value.report.final_failure.progress.observed_content
        assert "secret" not in caught.value.report.model_dump_json()

    @pytest.mark.parametrize(
        "admission,outcome,transitions",
        [
            (None, "admission_required", ["admission_required"]),
            (reject, "admission_rejected", ["admission_pending", "admission_rejected"]),
        ],
    )
    def should_require_explicit_permission_for_ambiguous_local_503(
        self, admission, outcome, transitions, messages
    ):
        from mojentic.llm.recovery import RecoveryError, RecoveryPolicy

        events = []
        with scripted_http([(503, {}, b"")]) as (host, requests):
            gateway = OllamaGateway(
                host=host,
                recovery_policy=RecoveryPolicy(
                    max_attempts=2, admission=admission, observer=events.append
                ),
            )

            with pytest.raises(RecoveryError) as caught:
                gateway.complete(model="test", messages=messages)

        assert len(requests) == 1
        assert caught.value.report.outcome == outcome
        assert caught.value.report.final_failure.acceptance == "unknown"
        assert [event.transition for event in events] == [
            "attempt_started",
            "attempt_failed",
            *transitions,
            "exhausted",
        ]

    @pytest.mark.parametrize(
        "header,state,delay,outcome,budget",
        [
            ("2", "seconds", 2, "succeeded", None),
            ("Thu, 01 Jan 1970 00:16:42 GMT", "date", 2, "succeeded", None),
            ("Thu, 01 Jan 1970 00:16:39 GMT", "date", 0.5, "succeeded", None),
            ("invalid-secret", "invalid", 0.5, "succeeded", None),
            (None, "absent", 0.5, "succeeded", None),
            ("31", "seconds", None, "delay_ceiling", None),
            ("2", "seconds", None, "budget_exhausted", 1),
        ],
    )
    def should_honor_retry_after_without_shortening_minima(
        self, header, state, delay, outcome, budget, messages
    ):
        from mojentic.llm.recovery import RecoveryError, RecoveryPolicy

        sleeps, events = [], []

        async def sleep(seconds):
            sleeps.append(seconds)

        headers = {} if header is None else {"Retry-After": header}
        with scripted_http([(429, headers, b""), (200, {}, frame())]) as (
            host,
            requests,
        ):
            gateway = OllamaGateway(
                host=host,
                recovery_policy=RecoveryPolicy(
                    max_attempts=2,
                    base_delay=1,
                    jitter=lambda ceiling: ceiling / 2,
                    wall=lambda: 1000,
                    budget=budget,
                    admission=allow,
                    sleeper=sleep,
                    observer=events.append,
                ),
            )
            try:
                gateway.complete(model="test", messages=messages)
                actual_outcome = "succeeded"
            except RecoveryError as error:
                actual_outcome = error.report.outcome

        assert actual_outcome == outcome
        assert len(requests) == (2 if outcome == "succeeded" else 1)
        assert sleeps == ([] if delay is None else [delay])
        failure = next(
            event.failure for event in events if event.transition == "attempt_failed"
        )
        assert failure.retry_after.state == state
        assert failure.progress.headers_received
        assert not failure.progress.semantic

    def should_not_follow_redirects_or_count_hidden_attempts(self, messages):
        from mojentic.llm.recovery import RecoveryError, RecoveryPolicy

        with scripted_http([(307, {"Location": "/api/chat"}, b"")]) as (host, requests):
            gateway = OllamaGateway(host=host, recovery_policy=RecoveryPolicy())

            with pytest.raises(RecoveryError) as caught:
                gateway.complete(model="test", messages=messages)

        assert len(requests) == 1
        assert caught.value.report.final_failure.http_status == 307

    def should_preserve_legacy_success_and_one_send_by_default(self, messages):
        with scripted_http([(200, {}, frame("legacy", thinking="reasoning"))]) as (
            host,
            requests,
        ):
            response = OllamaGateway(host=host).complete(
                model="test", messages=messages
            )

        assert len(requests) == 1
        assert (response.content, response.thinking, response.finish_reason) == (
            "legacy",
            "reasoning",
            "stop",
        )
        assert "recovery" not in response.metadata

    def should_expose_success_history_and_truthful_capabilities(self, messages):
        from mojentic.llm.recovery import RecoveryPolicy

        with scripted_http([(503, {}, b""), (200, {}, frame())]) as (host, requests):
            gateway = OllamaGateway(
                host=host,
                recovery_policy=RecoveryPolicy(
                    max_attempts=2, base_delay=0, admission=allow
                ),
            )
            response = gateway.complete(model="test", messages=messages)

        assert isinstance(
            response.recovery_report.history[0].inspect_cause(),
            __import__("httpx").HTTPStatusError,
        )
        assert response.recovery_report.history[0].inspect_response() == b""
        assert response.recovery_report.progress.delivered_content == len("answer")
        report = response.metadata["recovery"]
        assert len(requests) == report["identity"]["wire_attempt"] == 2
        assert len(report["history"]) == 1
        assert report["history"][0]["http_status"] == 503
        assert report["outcome"] == "succeeded"
        assert gateway.recovery_capabilities().model_dump() == {
            "ordinary_recovery": True,
            "structured_recovery": True,
            "streaming_recovery": False,
            "remote_cancellation": "unsupported",
            "inference_termination": "unknown",
            "idempotency": "unsupported",
            "exact_wire_capture": True,
        }


class DescribeRecoveryCancellation:
    async def should_leave_admission_pending_until_allowed(self, messages):
        from mojentic.llm.recovery import RecoveryPolicy

        pending, release = asyncio.Event(), asyncio.Event()

        async def admission(context):
            assert context.next_attempt == 2
            assert context.previous_identity == context.failure.identity
            pending.set()
            await release.wait()
            return "allow"

        with scripted_http([(503, {}, b""), (200, {}, frame())]) as (host, requests):
            gateway = OllamaGateway(
                host=host,
                recovery_policy=RecoveryPolicy(
                    max_attempts=2, base_delay=0, admission=admission
                ),
            )
            task = asyncio.create_task(
                gateway.complete_with_recovery(model="test", messages=messages)
            )
            await asyncio.wait_for(pending.wait(), 2)
            assert len(requests) == 1
            assert not task.done()
            release.set()
            response = await asyncio.wait_for(task, 2)

        assert response.content == "answer"
        assert len(requests) == 2

    @pytest.mark.parametrize(
        "phase,expected",
        [
            (
                "admission",
                ["attempt_started", "attempt_failed", "admission_pending", "cancelled"],
            ),
            (
                "backoff",
                [
                    "attempt_started",
                    "attempt_failed",
                    "admission_pending",
                    "admission_allowed",
                    "delay_scheduled",
                    "cancelled",
                ],
            ),
        ],
    )
    async def should_cancel_pending_waits_and_never_resend(
        self, phase, expected, messages
    ):
        from mojentic.llm.recovery import RecoveryCall, RecoveryError, RecoveryPolicy

        entered, closed = asyncio.Event(), asyncio.Event()
        call, events = RecoveryCall(), []

        async def wait(*args):
            entered.set()
            try:
                await asyncio.Event().wait()
            finally:
                closed.set()

        policy = RecoveryPolicy(
            max_attempts=2,
            admission=wait if phase == "admission" else allow,
            sleeper=wait if phase == "backoff" else asyncio.sleep,
            observer=events.append,
        )
        with scripted_http([(503, {}, b"failure")]) as (host, requests):
            gateway = OllamaGateway(host=host, recovery_policy=policy)
            task = asyncio.create_task(
                gateway.complete_with_recovery(
                    call=call, model="test", messages=messages
                )
            )
            await asyncio.wait_for(entered.wait(), 2)
            call.cancel()
            with pytest.raises(RecoveryError) as caught:
                await asyncio.wait_for(task, 1)

        assert closed.is_set()
        assert len(requests) == 1
        assert caught.value.report.outcome == "cancelled"
        assert len(caught.value.report.history) == 1
        assert caught.value.report.history[0].http_status == 503
        assert caught.value.report.final_failure.category == "cancellation"
        assert [event.transition for event in events] == expected

    async def should_cancel_active_request_retaining_headers_and_raw_progress(
        self, messages
    ):
        from mojentic.llm.recovery import RecoveryCall, RecoveryError, RecoveryPolicy

        call, entered, events = RecoveryCall(), asyncio.Event(), []

        def capture(event):
            if event.kind == "headers":
                entered.set()

        with scripted_http([(200, {}, (0.2, b"partial-secret"))]) as (host, requests):
            gateway = OllamaGateway(
                host=host,
                recovery_policy=RecoveryPolicy(
                    max_attempts=3,
                    wire_observer=capture,
                    observer=events.append,
                    admission=allow,
                ),
            )
            task = asyncio.create_task(
                gateway.complete_with_recovery(
                    call=call, model="test", messages=messages
                )
            )
            await asyncio.wait_for(entered.wait(), 2)
            call.cancel()
            with pytest.raises(RecoveryError) as caught:
                await asyncio.wait_for(task, 1)

        assert entered.is_set()
        assert len(requests) == 1
        assert caught.value.report.outcome == "cancelled"
        assert caught.value.report.final_failure.progress.headers_received
        assert [event.transition for event in events] == [
            "attempt_started",
            "attempt_failed",
            "cancelled",
        ]
        assert isinstance(caught.value.inspect_cause(), asyncio.CancelledError)

    async def should_cancel_before_dispatch_without_inventing_wire_attempt(
        self, messages
    ):
        from mojentic.llm.recovery import RecoveryCall, RecoveryError, RecoveryPolicy

        call = RecoveryCall()
        call.cancel()
        with scripted_http([]) as (host, requests):
            gateway = OllamaGateway(
                host=host, recovery_policy=RecoveryPolicy(max_attempts=3)
            )
            with pytest.raises(RecoveryError) as caught:
                await gateway.complete_with_recovery(
                    call=call, model="test", messages=messages
                )

        assert requests == []
        assert caught.value.report.identity.wire_attempt == 0
        assert caught.value.report.identity.attempt_id is None
        assert caught.value.report.history == ()

    async def should_expire_budget_while_admission_is_pending(self, messages):
        from mojentic.llm.recovery import RecoveryError, RecoveryPolicy

        closed = asyncio.Event()

        async def admission(context):
            try:
                await asyncio.Event().wait()
            finally:
                closed.set()

        with scripted_http([(504, {}, b"")]) as (host, requests):
            gateway = OllamaGateway(
                host=host,
                recovery_policy=RecoveryPolicy(
                    max_attempts=2, budget=0.02, base_delay=0, admission=admission
                ),
            )
            with pytest.raises(RecoveryError) as caught:
                await asyncio.wait_for(
                    gateway.complete_with_recovery(model="test", messages=messages), 2
                )

        assert closed.is_set()
        assert len(requests) == 1
        assert caught.value.report.outcome == "budget_exhausted"


class DescribeRecoveryToolSafety:
    @pytest.mark.parametrize("entrypoint", ["generate", "send"])
    def should_execute_tool_once_and_recover_only_the_subsequent_completion(
        self, entrypoint, messages, broker_factory
    ):
        from mojentic.llm.chat_session import ChatSession
        from mojentic.llm.completion_config import CompletionConfig
        from mojentic.llm.recovery import RecoveryPolicy
        from mojentic.llm.tools.llm_tool import LLMTool

        class CounterTool(LLMTool):
            def __init__(self):
                super().__init__()
                self.calls = []

            @property
            def descriptor(self):
                return {
                    "type": "function",
                    "function": {
                        "name": "counter",
                        "description": "Count once",
                        "parameters": {
                            "type": "object",
                            "properties": {},
                            "required": [],
                        },
                    },
                }

            def run(self, **kwargs):
                self.calls.append(kwargs)
                return "tool result"

        tool, events = CounterTool(), []
        tool_response = frame(
            "",
            thinking="native tool reasoning",
            tool_calls=[{"function": {"name": "counter", "arguments": {}}}],
        )
        with scripted_http(
            [(200, {}, tool_response), (503, {}, b""), (200, {}, frame("finished"))]
        ) as (host, requests):
            gateway = OllamaGateway(
                host=host,
                recovery_policy=RecoveryPolicy(
                    max_attempts=2,
                    base_delay=0,
                    admission=allow,
                    observer=events.append,
                ),
            )
            broker = broker_factory(gateway)
            config = CompletionConfig(max_tool_iterations=2)
            actions = {
                "generate": lambda: broker.generate(
                    messages, tools=[tool], config=config
                ),
                "send": lambda: ChatSession(broker, tools=[tool], config=config).send(
                    "payload-sentinel"
                ),
            }

            result = actions[entrypoint]()

        assert result == "finished"
        assert tool.calls == [{}]
        assert len(requests) == 3
        assert requests[1][1] == requests[2][1]
        payload = json.loads(requests[2][1])
        assert payload["messages"][-1]["role"] == "tool"
        assert payload["messages"][-1]["content"] == '"tool result"'
        starts = [
            event.identity for event in events if event.transition == "attempt_started"
        ]
        assert [identity.wire_attempt for identity in starts] == [1, 1, 2]
        assert (
            starts[0].logical_request_id
            != starts[1].logical_request_id
            == starts[2].logical_request_id
        )
        assert config.max_tool_iterations == 2

    def should_preserve_tool_depth_limit_across_recovered_completions(
        self, messages, broker_factory, mocker
    ):
        from mojentic.llm.completion_config import CompletionConfig
        from mojentic.llm.llm_broker import MaxToolIterationsExceededError
        from mojentic.llm.recovery import RecoveryPolicy
        from mojentic.llm.tools.llm_tool import LLMTool

        tool = mocker.Mock(spec=LLMTool)
        tool.name = "counter"
        tool.description = "Count"
        tool.descriptor = {
            "type": "function",
            "function": {"name": "counter", "parameters": {"type": "object"}},
        }
        tool.matches.return_value = True
        tool.run.return_value = "result"
        response = frame(
            "", tool_calls=[{"function": {"name": "counter", "arguments": {}}}]
        )
        with scripted_http(
            [(200, {}, response), (503, {}, b""), (200, {}, response)]
        ) as (host, requests):
            broker = broker_factory(
                OllamaGateway(
                    host=host,
                    recovery_policy=RecoveryPolicy(
                        max_attempts=2, base_delay=0, admission=allow
                    ),
                )
            )

            with pytest.raises(MaxToolIterationsExceededError):
                broker.generate(
                    messages,
                    tools=[tool],
                    config=CompletionConfig(max_tool_iterations=2),
                )

        assert len(requests) == 3
        assert tool.run.call_count == 2


class DescribeRecoveryEdgeEvidence:
    @pytest.mark.parametrize(
        "admission,outcome,count",
        [
            (None, "admission_required", 1),
            (reject, "admission_rejected", 1),
            (allow, "succeeded", 2),
        ],
    )
    def should_require_admission_after_an_actual_read_timeout(
        self, admission, outcome, count, messages
    ):
        import httpx

        from mojentic.llm.recovery import RecoveryError, RecoveryPolicy

        events = []
        with scripted_http([(200, {}, (0.1, frame())), (200, {}, frame())]) as (
            host,
            requests,
        ):
            gateway = OllamaGateway(
                host=host,
                timeout=httpx.Timeout(0.03),
                recovery_policy=RecoveryPolicy(
                    max_attempts=2,
                    base_delay=0,
                    admission=admission,
                    observer=events.append,
                ),
            )
            try:
                response = gateway.complete(model="test", messages=messages)
                actual_outcome = response.recovery_report.outcome
            except RecoveryError as error:
                actual_outcome = error.report.outcome

        assert len(requests) == count
        assert actual_outcome == outcome
        failure = next(
            event.failure for event in events if event.transition == "attempt_failed"
        )
        assert failure.category == "client_timeout"
        assert failure.acceptance == "unknown"
        assert failure.progress.headers_received
        assert failure.progress.raw_bytes == 0
        assert isinstance(failure.inspect_cause(), httpx.ReadTimeout)

    async def should_reject_after_a_pending_admission_without_another_wire_attempt(
        self, messages
    ):
        from mojentic.llm.recovery import RecoveryError, RecoveryPolicy

        pending, decide = asyncio.Event(), asyncio.Event()

        async def admission(context):
            pending.set()
            await decide.wait()
            return "reject"

        with scripted_http([(504, {}, b"")]) as (host, requests):
            gateway = OllamaGateway(
                host=host,
                recovery_policy=RecoveryPolicy(max_attempts=2, admission=admission),
            )
            task = asyncio.create_task(
                gateway.complete_with_recovery(model="test", messages=messages)
            )
            await asyncio.wait_for(pending.wait(), 2)
            assert len(requests) == 1
            assert not task.done()
            decide.set()
            with pytest.raises(RecoveryError) as caught:
                await asyncio.wait_for(task, 2)

        assert len(requests) == 1
        assert caught.value.report.outcome == "admission_rejected"
        assert caught.value.report.identity.wire_attempt == 1
        assert len(caught.value.report.history) == 1

    @pytest.mark.parametrize(
        "message",
        [
            {"content": "secret"},
            {"thinking": "secret", "content": ""},
            {
                "content": "",
                "tool_calls": [
                    {"function": {"name": "secret", "arguments": {"secret": "secret"}}}
                ],
            },
        ],
    )
    def should_prohibit_replay_of_each_observed_semantic_kind_when_capture_fails(
        self, message, messages
    ):
        from mojentic.llm.recovery import RecoveryError, RecoveryPolicy

        cause = OSError("secret")

        def capture(event):
            if event.kind == "body":
                raise cause

        body = frame(**message)
        with scripted_http([(200, {}, body)]) as (host, requests):
            gateway = OllamaGateway(
                host=host,
                recovery_policy=RecoveryPolicy(
                    max_attempts=3, wire_observer=capture, admission=allow
                ),
            )
            with pytest.raises(RecoveryError) as caught:
                gateway.complete(model="test", messages=messages)

        failure = caught.value.report.final_failure
        assert len(requests) == 1
        assert failure.progress.semantic
        assert failure.reason == "semantic_output"
        assert (
            failure.progress.delivered_content,
            failure.progress.delivered_reasoning,
            failure.progress.delivered_tool_fragments,
            failure.progress.delivered_tool_calls,
        ) == (0, 0, 0, 0)
        assert caught.value.inspect_cause() is cause
        assert failure.inspect_cause() is cause
        assert failure.inspect_response() == body
        assert "secret" not in failure.model_dump_json() + repr(failure) + str(
            caught.value
        )

    @pytest.mark.parametrize(
        "stage,count", [("request", 0), ("headers", 1), ("body", 1)]
    )
    def should_stop_on_capture_failure_without_inventing_wire_history(
        self, stage, count, messages
    ):
        from mojentic.llm.recovery import RecoveryError, RecoveryPolicy

        cause = OSError("secret")

        def capture(event):
            if event.kind == stage:
                raise cause

        with scripted_http([(503, {}, b"private")]) as (host, requests):
            gateway = OllamaGateway(
                host=host,
                recovery_policy=RecoveryPolicy(
                    max_attempts=3, wire_observer=capture, admission=allow
                ),
            )
            with pytest.raises(RecoveryError) as caught:
                gateway.complete(model="test", messages=messages)

        assert len(requests) == count
        assert caught.value.report.identity.wire_attempt == count
        assert len(caught.value.report.history) == count
        assert caught.value.inspect_cause() is cause
        assert not caught.value.report.final_failure.eligible

    @pytest.mark.parametrize(
        "transition",
        ["attempt_started", "attempt_failed", "exhausted", "attempt_succeeded"],
    )
    def should_keep_observer_exceptions_private_and_prohibit_replay(
        self, transition, messages
    ):
        from mojentic.llm.recovery import RecoveryError, RecoveryPolicy

        cause = OSError("secret")

        def observe(event):
            if event.transition == transition:
                raise cause

        replies = {
            "attempt_started": (200, {}, frame()),
            "attempt_succeeded": (200, {}, frame()),
            "attempt_failed": (400, {}, b""),
            "exhausted": (400, {}, b""),
        }
        with scripted_http([replies[transition]]) as (host, requests):
            gateway = OllamaGateway(
                host=host,
                recovery_policy=RecoveryPolicy(max_attempts=3, observer=observe),
            )
            with pytest.raises(RecoveryError) as caught:
                gateway.complete(model="test", messages=messages)

        assert len(requests) <= 1
        assert caught.value.inspect_cause() is cause
        assert "secret" not in str(caught.value) + caught.value.report.model_dump_json()

    def should_freeze_images_and_controls_once_before_admission(
        self, tmp_path, messages
    ):
        from mojentic.llm.completion_config import CompletionConfig, ResponseFormat
        from mojentic.llm.recovery import RecoveryPolicy

        image = tmp_path / "input.png"
        image.write_bytes(b"original image bytes")
        messages[0].image_paths = [str(image)]
        config = CompletionConfig(response_format=ResponseFormat(type="json_object"))

        async def admission(context):
            image.write_bytes(b"replaced image bytes")
            messages[0].content = "mutated content"
            config.temperature = 0.1
            return "allow"

        with scripted_http([(503, {}, b""), (200, {}, frame())]) as (host, requests):
            gateway = OllamaGateway(
                host=host,
                recovery_policy=RecoveryPolicy(
                    max_attempts=2, base_delay=0, admission=admission
                ),
            )
            gateway.complete(model="test", messages=messages, config=config)

        assert len(requests) == 2
        assert requests[0][1] == requests[1][1]
        payload = json.loads(requests[1][1])
        assert payload["messages"][0]["images"] == [
            base64.b64encode(b"original image bytes").decode()
        ]
        assert payload["messages"][0]["content"] == "payload-sentinel"
        assert payload["options"]["temperature"] == 1
        assert payload["format"] == "json"

    def should_allow_active_generation_to_finish_after_recovery_deadline(
        self, messages
    ):
        from mojentic.llm.recovery import RecoveryPolicy

        now = [10.0]

        def capture(event):
            if event.kind == "headers" and event.identity.wire_attempt == 2:
                now[0] = 1000.0

        with scripted_http([(503, {}, b""), (200, {}, frame())]) as (host, requests):
            gateway = OllamaGateway(
                host=host,
                recovery_policy=RecoveryPolicy(
                    max_attempts=2,
                    base_delay=0,
                    admission=allow,
                    deadline=11,
                    monotonic=lambda: now[0],
                    wire_observer=capture,
                ),
            )
            response = gateway.complete(model="test", messages=messages)

        assert len(requests) == 2
        assert response.content == "answer"
        assert response.recovery_report.outcome == "succeeded"

    def should_refuse_admission_that_consumed_the_recovery_budget(self, messages):
        from mojentic.llm.recovery import RecoveryError, RecoveryPolicy

        now = [10.0]

        async def admission(context):
            now[0] += 2
            return "allow"

        with scripted_http([(503, {}, b"")]) as (host, requests):
            gateway = OllamaGateway(
                host=host,
                recovery_policy=RecoveryPolicy(
                    max_attempts=2,
                    base_delay=0,
                    admission=admission,
                    budget=1,
                    monotonic=lambda: now[0],
                ),
            )
            with pytest.raises(RecoveryError) as caught:
                gateway.complete(model="test", messages=messages)

        assert len(requests) == 1
        assert caught.value.report.outcome == "budget_exhausted"

    async def should_make_native_task_cancellation_authoritative(self, messages):
        from mojentic.llm.recovery import RecoveryError, RecoveryPolicy

        entered, closed = asyncio.Event(), asyncio.Event()

        async def admission(context):
            entered.set()
            try:
                await asyncio.Event().wait()
            finally:
                closed.set()

        with scripted_http([(503, {}, b"")]) as (host, requests):
            gateway = OllamaGateway(
                host=host,
                recovery_policy=RecoveryPolicy(max_attempts=2, admission=admission),
            )
            task = asyncio.create_task(
                gateway.complete_with_recovery(model="test", messages=messages)
            )
            await asyncio.wait_for(entered.wait(), 2)
            task.cancel()
            with pytest.raises(RecoveryError) as caught:
                await task

        assert closed.is_set()
        assert len(requests) == 1
        assert caught.value.report.outcome == "cancelled"


class DescribePublicCancellationAndMetadata:
    async def should_cancel_a_synchronous_chat_session_during_admission(
        self, broker_factory
    ):
        from mojentic.llm.chat_session import ChatSession
        from mojentic.llm.recovery import RecoveryCall, RecoveryError, RecoveryPolicy

        entered, finished = threading.Event(), threading.Event()
        call = RecoveryCall()

        async def admission(context):
            entered.set()
            try:
                await asyncio.sleep(100)
            finally:
                finished.set()

        with scripted_http([(503, {}, b"")]) as (host, requests):
            gateway = OllamaGateway(
                host=host,
                recovery_call=call,
                recovery_policy=RecoveryPolicy(max_attempts=3, admission=admission),
            )
            session = ChatSession(broker_factory(gateway))
            task = asyncio.create_task(asyncio.to_thread(session.send, "hello"))
            await asyncio.wait_for(asyncio.to_thread(entered.wait, 2), 3)
            call.cancel()
            with pytest.raises(RecoveryError) as caught:
                await asyncio.wait_for(task, 1)

        assert entered.is_set() and finished.is_set()
        assert len(requests) == 1
        assert caught.value.report.outcome == "cancelled"
        assert caught.value.report.history[0].http_status == 503
        assert len(session.messages) == 2

    @pytest.mark.parametrize(
        "value,expected",
        [
            (
                "bd38be36-6698-43f1-9d34-7452b980f471",
                None,
            ),
            ("credential-payload-echo-secret", None),
        ],
    )
    def should_expose_only_validated_provider_request_ids(
        self, value, expected, messages
    ):
        from mojentic.llm.recovery import RecoveryError, RecoveryPolicy

        with scripted_http([(503, {"X-Request-ID": value}, b"private")]) as (
            host,
            requests,
        ):
            gateway = OllamaGateway(host=host, recovery_policy=RecoveryPolicy())
            with pytest.raises(RecoveryError) as caught:
                gateway.complete(model="test", messages=messages)

        assert len(requests) == 1
        assert caught.value.report.final_failure.provider_request_id == expected
        assert "secret" not in caught.value.report.model_dump_json()

    def should_structure_invalid_image_preparation_without_a_wire_attempt(
        self, tmp_path, messages
    ):
        from mojentic.llm.recovery import RecoveryError, RecoveryPolicy

        messages[0].image_paths = [str(tmp_path / "secret-missing.png")]
        with scripted_http([]) as (host, requests):
            gateway = OllamaGateway(host=host, recovery_policy=RecoveryPolicy())
            with pytest.raises(RecoveryError) as caught:
                gateway.complete(model="test", messages=messages)

        assert requests == []
        assert caught.value.report.identity.wire_attempt == 0
        assert caught.value.report.history == ()
        assert caught.value.report.final_failure.acceptance == "no"
        assert isinstance(caught.value.inspect_cause(), ValueError)
        assert "secret" not in str(caught.value) + caught.value.report.model_dump_json()
