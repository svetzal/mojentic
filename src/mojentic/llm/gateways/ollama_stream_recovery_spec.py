"""Public streaming recovery contracts over scripted loopback HTTP."""

import asyncio

import pytest

from mojentic.llm.gateways.models import LLMMessage
from mojentic.llm.gateways.ollama import OllamaGateway
from mojentic.llm.gateways.ollama_recovery_spec import frame, scripted_http
from mojentic.llm.recovery import RecoveryError, RecoveryPolicy


class DescribeOllamaStreamRecovery:
    def should_retain_observed_semantics_when_capture_fails_without_delivery(self):
        cause = OSError("sensitive capture failure")
        captures = []
        lifecycle = []

        def capture(event):
            captures.append(event)
            if event.kind == "body":
                raise cause

        with scripted_http([(200, {}, frame("évidence") + b"\n")]) as (host, requests):
            gateway = OllamaGateway(
                host=host,
                recovery_policy=RecoveryPolicy(
                    max_attempts=3, wire_observer=capture, observer=lifecycle.append
                ),
            )
            with pytest.raises(RecoveryError) as caught:
                list(
                    gateway.complete_stream(
                        model="test", messages=[LLMMessage(content="secret")]
                    )
                )

        failure = caught.value.report.final_failure
        assert len(requests) == 1
        assert failure.progress.observed_content
        assert failure.progress.delivered_content == 0
        assert failure.reason == "capture_failed"
        assert failure.inspect_cause() is cause
        assert failure.inspect_response() == frame("évidence") + b"\n"
        assert [event.transition for event in lifecycle] == [
            "attempt_started",
            "attempt_failed",
            "interrupted",
        ]


async def allow(context):
    return "allow"


async def collect(gateway, call=None, **args):
    return [
        event
        async for event in gateway.complete_stream_with_recovery(
            model="test",
            messages=[LLMMessage(content="payload-sentinel")],
            call=call,
            **args,
        )
    ]


def ndjson(**fields):
    import json

    return json.dumps(fields, ensure_ascii=False).encode("utf-8") + b"\n"


class DescribeStreamingWireEvidence:
    @pytest.mark.parametrize(
        "retry_after,state,delay",
        [
            ("2", "seconds", 2),
            ("Thu, 01 Jan 1970 00:00:03 GMT", "date", 3),
            ("invalid", "invalid", 0),
        ],
    )
    async def should_recover_503_with_exact_authenticated_bytes_and_identity(
        self, retry_after, state, delay
    ):
        import base64
        import json

        from mojentic.llm.completion_config import CompletionConfig
        from mojentic.llm.recovery import RecoveryPolicy

        captures, lifecycle, delays = [], [], []

        async def sleep(seconds):
            delays.append(seconds)

        with scripted_http(
            [
                (503, {"Retry-After": retry_after}, b"busy"),
                (200, {}, frame("é") + b"\n"),
            ]
        ) as (host, requests):
            gateway = OllamaGateway(
                host=host.replace("http://", "http://user:password@"),
                headers={"X-Payload": "payload-sentinel"},
                recovery_policy=RecoveryPolicy(
                    max_attempts=2,
                    base_delay=0,
                    wall=lambda: 0,
                    admission=allow,
                    sleeper=sleep,
                    wire_observer=captures.append,
                    observer=lifecycle.append,
                ),
            )
            events = await collect(
                gateway,
                config=CompletionConfig(reasoning_effort="high", temperature=0.2),
            )

        terminal = events[-1]
        assert terminal.kind == "completed"
        assert terminal.response.content == "é"
        assert terminal.report.progress.delivered_content == 2
        assert terminal.report.identity.wire_attempt == 2
        assert len(terminal.report.history) == 1
        assert terminal.report.history[0].retry_after.state == state
        assert delays == [delay]
        assert len(requests) == 2
        assert requests[0][1] == requests[1][1]
        payload = json.loads(requests[0][1])
        assert payload["stream"] is True
        assert payload["think"] is True
        assert payload["options"]["temperature"] == 0.2
        sent = [capture for capture in captures if capture.kind == "request"]
        assert [capture.body for capture in sent] == [
            request[1] for request in requests
        ]
        expected_auth = "Basic " + base64.b64encode(b"user:password").decode()
        assert [dict(capture.headers)["authorization"] for capture in sent] == [
            expected_auth
        ] * 2
        assert [request[2]["Authorization"] for request in requests] == [
            expected_auth
        ] * 2
        assert len({capture.identity.attempt_id for capture in sent}) == 2
        assert len({capture.identity.logical_request_id for capture in sent}) == 1
        assert all(capture.identity.attempt_id is not None for capture in sent)
        assert [event.frame_index for event in events if event.kind == "progress"] == [
            1
        ]
        safe = "".join(
            event.model_dump_json() + repr(event) for event in lifecycle + events
        )
        assert "payload-sentinel" not in safe
        assert "password" not in safe
        assert [event.transition for event in lifecycle] == [
            "attempt_started",
            "attempt_failed",
            "admission_pending",
            "admission_allowed",
            "delay_scheduled",
            "retry_started",
            "attempt_started",
            "attempt_succeeded",
        ]

    @pytest.mark.parametrize(
        "admission,outcome,count",
        [(None, "admission_required", 1), (allow, "attempts_exhausted", 3)],
    )
    async def should_bound_persistent_504_history(self, admission, outcome, count):
        import httpx

        with scripted_http([(504, {}, b"secret")] * 3) as (host, requests):
            events = await collect(
                OllamaGateway(
                    host=host,
                    recovery_policy=RecoveryPolicy(
                        max_attempts=3, base_delay=0, admission=admission
                    ),
                )
            )
        error = events[-1].error
        assert events[-1].outcome.value == outcome
        assert len(requests) == count
        assert len(error.report.history) == count
        assert [failure.http_status for failure in error.report.history] == [
            504
        ] * count
        assert [
            failure.identity.wire_attempt for failure in error.report.history
        ] == list(range(1, count + 1))
        assert (
            len({failure.identity.attempt_id for failure in error.report.history})
            == count
        )
        assert all(
            isinstance(failure.inspect_cause(), httpx.HTTPStatusError)
            for failure in error.report.history
        )
        assert all(
            failure.inspect_response() == b"secret" for failure in error.report.history
        )

    async def should_refuse_excessive_retry_after_without_admitting(self):
        decisions = []

        async def admit(context):
            decisions.append(context)
            return "allow"

        with scripted_http([(503, {"Retry-After": "100"}, b"")]) as (host, requests):
            events = await collect(
                OllamaGateway(
                    host=host,
                    recovery_policy=RecoveryPolicy(
                        max_attempts=2, delay_ceiling=5, admission=admit
                    ),
                )
            )
        assert len(requests) == 1
        assert decisions == []
        assert events[-1].outcome.value == "delay_ceiling"
        assert events[-1].report.final_failure.retry_after.delay == 100

    @pytest.mark.parametrize("status", [400, 401, 403])
    async def should_retain_truncated_permanent_status_and_transport_cause(
        self, status
    ):
        import httpx

        with scripted_http(
            [(status, {"Content-Length": "100", "X-Secret": "secret"}, b"partial")]
        ) as (host, requests):
            events = await collect(
                OllamaGateway(
                    host=host,
                    recovery_policy=RecoveryPolicy(
                        max_attempts=3,
                        admission=allow,
                        retryable_statuses=frozenset({status}),
                        retryable_categories=frozenset({"transport", "http"}),
                    ),
                )
            )
        failure = events[-1].report.final_failure
        assert len(requests) == 1
        assert not failure.eligible
        assert failure.reason == "permanent"
        assert failure.http_status == status
        assert failure.category == "transport"
        assert failure.inspect_response() == b"partial"
        assert dict(failure.inspect_headers())["x-secret"] == "secret"
        assert isinstance(failure.inspect_cause(), httpx.RemoteProtocolError)
        assert failure.progress.raw_bytes == 7

    @pytest.mark.parametrize(
        "message,field",
        [
            ({"content": "é"}, "delivered_content"),
            ({"thinking": "é"}, "delivered_reasoning"),
            (
                {"tool_calls": [{"function": {"name": "tool", "arguments": {}}}]},
                "delivered_tool_fragments",
            ),
        ],
    )
    async def should_interrupt_after_semantic_delivery_without_replay(
        self, message, field
    ):
        partial = ndjson(done=False, message={"role": "assistant", **message})
        with scripted_http(
            [(200, {"Content-Length": str(len(partial) + 50)}, partial)]
        ) as (host, requests):
            events = await collect(
                OllamaGateway(
                    host=host,
                    recovery_policy=RecoveryPolicy(max_attempts=3, admission=allow),
                )
            )
        assert len(requests) == 1
        assert events[-1].kind == "failed"
        assert events[-1].outcome.value == "interrupted"
        assert getattr(events[-1].progress, field) > 0
        assert events[-1].report.final_failure.reason == "semantic_output"
        assert not any(event.kind == "completed" for event in events)

    async def should_allow_keepalive_only_transport_recovery(self):
        with scripted_http(
            [
                (200, {"Content-Length": "100"}, b"\n:keepalive\n"),
                (200, {}, frame("answer") + b"\n"),
            ]
        ) as (host, requests):
            events = await collect(
                OllamaGateway(
                    host=host,
                    recovery_policy=RecoveryPolicy(
                        max_attempts=2, base_delay=0, admission=allow
                    ),
                )
            )
        assert len(requests) == 2
        assert events[-1].kind == "completed"
        failure = events[-1].report.history[0]
        assert failure.progress.raw_bytes == len(b"\n:keepalive\n")
        assert not failure.progress.semantic
        assert failure.eligible

    async def should_reject_admission_without_resending(self):
        contexts = []

        async def reject(context):
            contexts.append(context)
            return "reject"

        with scripted_http([(503, {}, b"")]) as (host, requests):
            events = await collect(
                OllamaGateway(
                    host=host,
                    recovery_policy=RecoveryPolicy(max_attempts=3, admission=reject),
                )
            )
        assert len(requests) == 1
        assert events[-1].outcome.value == "admission_rejected"
        assert contexts[0].next_attempt == 2
        assert contexts[0].previous_identity == events[-1].identity


class DescribeStreamTelemetry:
    async def should_emit_exact_length_terminal_progress_metrics_then_failure(self):
        terminal = ndjson(
            model="reported-model",
            done=True,
            done_reason="length",
            message={
                "role": "assistant",
                "content": "é",
                "thinking": "考",
                "tool_calls": [
                    {"function": {"name": "tool", "arguments": {"secret": "value"}}}
                ],
            },
            prompt_eval_count=12,
            eval_count=4,
            total_duration=900,
            load_duration=3,
            prompt_eval_duration=40,
            eval_duration=70,
        )
        with scripted_http([(200, {}, terminal)]) as (host, requests):
            events = await collect(
                OllamaGateway(
                    host=host,
                    recovery_policy=RecoveryPolicy(max_attempts=3, admission=allow),
                )
            )
        assert len(requests) == 1
        assert [event.kind for event in events] == ["progress", "metrics", "failed"]
        assert events[0].frame_progress.model_dump() == {
            "provider": "ollama",
            "done": True,
            "content_bytes": 2,
            "reasoning_bytes": 3,
            "tool_call_count": 1,
            "accumulated_tool_call_count": 0,
        }
        assert events[1].metrics.provider_model == "reported-model"
        assert events[1].metrics.finish_reason == "length"
        assert events[1].metrics.model_dump(exclude_none=True) == {
            "provider": "ollama",
            "prompt_eval_count": 12,
            "eval_count": 4,
            "total_duration": 900,
            "load_duration": 3,
            "prompt_eval_duration": 40,
            "eval_duration": 70,
            "tokens_per_second": 4 / (70 / 1_000_000_000),
        }
        assert [event.frame_index for event in events[:2]] == [1, 1]
        assert events[0].identity == events[1].identity == events[2].identity
        progress = events[-1].progress
        assert progress.observed_content and progress.observed_reasoning
        assert progress.observed_tool_fragments == 1
        assert progress.completed_tool_calls == 0
        assert (
            progress.delivered_content
            == progress.delivered_reasoning
            == progress.delivered_tool_calls
            == 0
        )
        assert events[-1].outcome.value == "interrupted"

    @pytest.mark.parametrize(
        "fields",
        [
            {"done": "yes"},
            {"eval_count": -1},
            {"eval_count": True},
            {"message": {"content": 42}},
            {"message": {"tool_calls": "invalid"}},
            {
                "message": {
                    "tool_calls": [
                        {"id": 42, "function": {"name": "tool", "arguments": {}}}
                    ]
                }
            },
            {"model": 4},
        ],
    )
    async def should_emit_no_fabricated_telemetry_for_malformed_frames(self, fields):
        data = {
            "done": True,
            "done_reason": "stop",
            "message": {"content": ""},
        } | fields
        with scripted_http([(200, {}, ndjson(**data))]) as (host, requests):
            events = await collect(
                OllamaGateway(
                    host=host,
                    recovery_policy=RecoveryPolicy(max_attempts=2, admission=allow),
                )
            )
        assert len(requests) == 1
        assert [event.kind for event in events] == ["failed"]
        assert events[-1].report.final_failure.category == "protocol"

    async def should_preserve_only_reported_completion_evidence(self):
        data = ndjson(
            model="actual-model", done=False, message={"content": "é"}, load_duration=8
        )
        data += ndjson(
            done=True, done_reason="stop", message={}, eval_count=3, eval_duration=50
        )
        with scripted_http([(200, {}, data)]) as (host, requests):
            events = await collect(
                OllamaGateway(host=host, recovery_policy=RecoveryPolicy())
            )
        response = events[-1].response
        assert len(requests) == 1
        assert response.model == "actual-model"
        assert response.finish_reason == "stop"
        assert response.usage == {"eval_count": 3}
        assert response.metadata == {"load_duration": 8, "eval_duration": 50}
        assert events[-1].report.progress.delivered_content == 2
        assert [event.frame_index for event in events if event.kind == "progress"] == [
            1,
            2,
        ]
        assert events[-2].metrics.finish_reason == "stop"
        assert events[-2].metrics.model_dump(exclude_none=True) == {
            "provider": "ollama",
            "eval_count": 3,
            "eval_duration": 50,
            "tokens_per_second": 60_000_000,
        }


class DescribeStreamCancellation:
    @pytest.mark.parametrize("phase", ["admission", "backoff"])
    async def should_cancel_pending_decisions_and_delays_preserving_failed_attempt(
        self, phase
    ):
        import asyncio

        import httpx

        from mojentic.llm.recovery import RecoveryCall

        entered, closed = asyncio.Event(), asyncio.Event()
        call, lifecycle = RecoveryCall(), []

        async def pending(value):
            entered.set()
            try:
                await asyncio.Event().wait()
            finally:
                closed.set()

        policy = RecoveryPolicy(
            max_attempts=3,
            base_delay=0,
            observer=lifecycle.append,
            admission={"admission": pending, "backoff": allow}[phase],
            sleeper={"admission": asyncio.sleep, "backoff": pending}[phase],
        )
        with scripted_http([(504, {}, b"failed")]) as (host, requests):
            task = asyncio.create_task(
                collect(OllamaGateway(host=host, recovery_policy=policy), call)
            )
            await asyncio.wait_for(entered.wait(), 2)
            assert len(requests) == 1
            assert not task.done()
            call.cancel()
            events = await asyncio.wait_for(task, 2)
        error = events[-1].error
        assert closed.is_set()
        assert len(requests) == 1
        assert events[-1].outcome.value == "cancelled"
        assert len(error.report.history) == 1
        assert error.report.history[0].http_status == 504
        assert isinstance(error.inspect_cause(0), httpx.HTTPStatusError)
        assert isinstance(error.inspect_cause(), asyncio.CancelledError)
        transitions = [event.transition for event in lifecycle]
        assert transitions.count("attempt_failed") == 1
        assert transitions.count("cancelled") == 1
        assert transitions.index("attempt_failed") < transitions.index("cancelled")
        assert "attempt_succeeded" not in transitions

    @pytest.mark.parametrize(
        "done_reason,category,cause_type",
        [
            ("stop", "cancellation", asyncio.CancelledError),
            ("length", "protocol", ValueError),
        ],
    )
    @pytest.mark.parametrize("consumed", [1, 2])
    async def should_cancel_terminal_telemetry_while_consumer_is_paused(
        self, done_reason, category, cause_type, consumed
    ):
        import asyncio
        import threading

        from mojentic.llm.recovery import RecoveryCall

        call, lifecycle, cancelled = RecoveryCall(), [], threading.Event()

        def observe(event):
            lifecycle.append(event)
            if event.transition == "cancelled":
                cancelled.set()

        terminal = ndjson(
            model="test",
            done=True,
            done_reason=done_reason,
            message={
                "content": "",
                "tool_calls": [{"function": {"name": "tool", "arguments": {}}}],
            },
            eval_count=0,
            total_duration=20,
        )
        with scripted_http([(200, {}, terminal)]) as (host, requests):
            gateway = OllamaGateway(
                host=host,
                recovery_policy=RecoveryPolicy(observer=observe),
                recovery_call=call,
            )
            stream = gateway.complete_stream_with_recovery(
                model="test", messages=[LLMMessage(content="secret")]
            )
            initial = [await anext(stream) for _ in range(consumed)]
            assert [event.kind for event in initial] == ["progress", "metrics"][
                :consumed
            ]
            call.cancel()
            assert await asyncio.to_thread(cancelled.wait, 2)
            remaining = [event async for event in stream]
        assert len(requests) == 1
        assert [event.kind for event in remaining] == ["failed"]
        assert remaining[0].outcome.value == "cancelled"
        assert remaining[0].progress.delivered_tool_calls == 0
        assert remaining[0].progress.delivered_tool_fragments == 0
        transitions = [event.transition for event in lifecycle]
        assert (
            transitions.count("attempt_failed") == transitions.count("cancelled") == 1
        )
        assert transitions.index("attempt_failed") < transitions.index("cancelled")
        assert "attempt_succeeded" not in transitions
        assert remaining[0].report.history[0].category == category
        assert isinstance(remaining[0].report.history[0].inspect_cause(), cause_type)

    async def should_cancel_buffered_terminal_capture_before_any_delivery(self):
        from mojentic.llm.recovery import RecoveryCall

        call, captures, lifecycle = RecoveryCall(), [], []

        def capture(event):
            captures.append(event)
            if event.kind == "body":
                call.cancel()

        with scripted_http([(200, {}, frame("") + b"\n")]) as (host, requests):
            events = await collect(
                OllamaGateway(
                    host=host,
                    recovery_policy=RecoveryPolicy(
                        wire_observer=capture, observer=lifecycle.append
                    ),
                ),
                call,
            )
        assert len(requests) == 1
        assert [event.kind for event in events] == ["failed"]
        assert events[-1].outcome.value == "cancelled"
        assert [event.transition for event in lifecycle] == [
            "attempt_started",
            "attempt_failed",
            "cancelled",
        ]
        assert events[-1].report.progress.raw_bytes == len(frame("") + b"\n")

    async def should_close_active_request_on_cancellation(self):
        import asyncio
        import threading
        from contextlib import contextmanager
        from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

        from mojentic.llm.recovery import RecoveryCall

        entered, socket_closed = threading.Event(), threading.Event()
        requests = []

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                requests.append(self.rfile.read(int(self.headers["Content-Length"])))
                self.send_response(200)
                self.send_header("Content-Length", "100")
                self.end_headers()
                self.wfile.flush()
                entered.set()
                self.connection.settimeout(2)
                if self.rfile.read(1) == b"":
                    socket_closed.set()

            def log_message(self, *args):
                pass

        @contextmanager
        def active_http():
            server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
            thread = threading.Thread(
                target=lambda: server.serve_forever(poll_interval=0.01), daemon=True
            )
            thread.start()
            try:
                yield f"http://127.0.0.1:{server.server_port}"
            finally:
                server.shutdown()
                server.server_close()
                thread.join()

        call, lifecycle = RecoveryCall(), []
        with active_http() as host:
            task = asyncio.create_task(
                collect(
                    OllamaGateway(
                        host=host,
                        recovery_policy=RecoveryPolicy(
                            max_attempts=3, observer=lifecycle.append
                        ),
                    ),
                    call,
                )
            )
            assert await asyncio.to_thread(entered.wait, 2)
            call.cancel()
            events = await asyncio.wait_for(task, 2)
            assert await asyncio.to_thread(socket_closed.wait, 2)
        assert len(requests) == 1
        assert [event.kind for event in events] == ["failed"]
        assert events[-1].outcome.value == "cancelled"
        assert [event.transition for event in lifecycle] == [
            "attempt_started",
            "attempt_failed",
            "cancelled",
        ]


@pytest.fixture
def counter_tool():
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
                    "parameters": {"type": "object", "properties": {}, "required": []},
                },
            }

        def run(self, **kwargs):
            self.calls.append(kwargs)
            return "tool result"

    return CounterTool()


class DescribeStreamCallerSafety:
    @pytest.mark.parametrize("entrypoint", ["broker", "session"])
    @pytest.mark.parametrize("failure_kind", ["exhaustion", "partial"])
    def should_execute_completed_tool_once_and_preserve_subsequent_failure(
        self, entrypoint, failure_kind, counter_tool, mocker
    ):
        import json

        from mojentic.llm.chat_session import ChatSession
        from mojentic.llm.completion_config import CompletionConfig
        from mojentic.llm.gateways.tokenizer_gateway import TokenizerGateway
        from mojentic.llm.llm_broker import LLMBroker

        tool_data = (
            frame("", tool_calls=[{"function": {"name": "counter", "arguments": {}}}])
            + b"\n"
        )
        partial = ndjson(done=False, message={"content": "partial"})
        replies = {
            "exhaustion": [(504, {}, b"failed"), (504, {}, b"failed")],
            "partial": [(200, {"Content-Length": str(len(partial) + 50)}, partial)],
        }
        expected_count = {"exhaustion": 3, "partial": 2}[failure_kind]
        lifecycle = []
        tokenizer = mocker.Mock(spec=TokenizerGateway)
        tokenizer.encode.return_value = []
        config = CompletionConfig(max_tool_iterations=2)
        with scripted_http([(200, {}, tool_data)] + replies[failure_kind]) as (
            host,
            requests,
        ):
            gateway = OllamaGateway(
                host=host,
                recovery_policy=RecoveryPolicy(
                    max_attempts=2,
                    base_delay=0,
                    admission=allow,
                    observer=lifecycle.append,
                ),
            )
            broker = LLMBroker("test", gateway=gateway, tokenizer=tokenizer)
            session = ChatSession(
                broker, tools=[counter_tool], tokenizer_gateway=tokenizer, config=config
            )
            actions = {
                "broker": lambda: broker.generate_stream(
                    [LLMMessage(content="query")], tools=[counter_tool], config=config
                ),
                "session": lambda: session.send_stream("query"),
            }
            with pytest.raises(RecoveryError) as caught:
                list(actions[entrypoint]())
        assert counter_tool.calls == [{}]
        assert len(requests) == expected_count
        error = caught.value
        assert (
            error.report.outcome
            == {"exhaustion": "attempts_exhausted", "partial": "interrupted"}[
                failure_kind
            ]
        )
        starts = [
            event.identity
            for event in lifecycle
            if event.transition == "attempt_started"
        ]
        assert starts[0].logical_request_id != starts[1].logical_request_id
        assert all(
            identity.logical_request_id == starts[1].logical_request_id
            for identity in starts[1:]
        )
        assert [identity.wire_attempt for identity in starts] == [1] + list(
            range(1, expected_count)
        )
        assert all(request[1] == requests[1][1] for request in requests[1:])
        assert json.loads(requests[1][1])["messages"][-1]["role"] == "tool"
        assert not any(
            message.role.value == "assistant" and message.content == "partial"
            for message in session.messages
        )
        assert not any(
            message.role.value == "assistant" and message.content == "failed"
            for message in session.messages
        )
        assert error.report.identity.wire_attempt == expected_count - 1

    def should_keep_retry_accounting_separate_from_tool_depth(
        self, counter_tool, mocker
    ):
        from mojentic.llm.completion_config import CompletionConfig
        from mojentic.llm.gateways.tokenizer_gateway import TokenizerGateway
        from mojentic.llm.llm_broker import LLMBroker

        tokenizer = mocker.Mock(spec=TokenizerGateway)
        tokenizer.encode.return_value = []
        tool_data = (
            frame("", tool_calls=[{"function": {"name": "counter", "arguments": {}}}])
            + b"\n"
        )
        lifecycle = []
        with scripted_http(
            [
                (503, {}, b""),
                (200, {}, tool_data),
                (503, {}, b""),
                (200, {}, frame("finished") + b"\n"),
            ]
        ) as (host, requests):
            broker = LLMBroker(
                "test",
                tokenizer=tokenizer,
                gateway=OllamaGateway(
                    host=host,
                    recovery_policy=RecoveryPolicy(
                        max_attempts=2,
                        base_delay=0,
                        admission=allow,
                        observer=lifecycle.append,
                    ),
                ),
            )
            content = list(
                broker.generate_stream(
                    [LLMMessage(content="query")],
                    tools=[counter_tool],
                    config=CompletionConfig(max_tool_iterations=2),
                )
            )
        assert content == ["finished"]
        assert counter_tool.calls == [{}]
        assert len(requests) == 4
        assert requests[0][1] == requests[1][1]
        assert requests[2][1] == requests[3][1]
        assert [
            event.identity.wire_attempt
            for event in lifecycle
            if event.transition == "attempt_started"
        ] == [1, 2, 1, 2]

    def should_characterize_retries_disabled_legacy_stream(self):
        from ollama import ResponseError

        with scripted_http(
            [
                (
                    200,
                    {},
                    ndjson(
                        done=True,
                        done_reason="length",
                        message={"role": "assistant", "content": "legacy"},
                    ),
                )
            ]
        ) as (host, requests):
            chunks = list(
                OllamaGateway(host=host).complete_stream(
                    model="test", messages=[LLMMessage(content="query")]
                )
            )
        assert [chunk.content for chunk in chunks] == ["legacy"]
        assert len(requests) == 1
        with (
            scripted_http([(503, {}, b'{"error":"busy"}')]) as (host, requests),
            pytest.raises(ResponseError) as caught,
        ):
            list(
                OllamaGateway(host=host).complete_stream(
                    model="test", messages=[LLMMessage(content="query")]
                )
            )
        assert caught.value.status_code == 503
        assert len(requests) == 1

    async def should_keep_raw_event_api_single_turn_with_recovery_configured(self):
        from mojentic.llm.completion_config import CompletionConfig
        from mojentic.llm.gateways.stream_events import StreamError, StreamErrorReason

        with scripted_http([(503, {}, b'{"error":"busy"}')]) as (host, requests):
            gateway = OllamaGateway(
                host=host,
                recovery_policy=RecoveryPolicy(max_attempts=3, admission=allow),
            )
            events = list(
                gateway.complete_stream_events(
                    "test", [LLMMessage(content="query")], CompletionConfig()
                )
            )
        assert len(requests) == 1
        assert len(events) == 1
        assert isinstance(events[0], StreamError)
        assert events[0].reason == StreamErrorReason.PROVIDER_ERROR


class DescribeStreamPrivacyAndCapture:
    @pytest.mark.parametrize(
        "semantic",
        [
            {"content": "payload-sentinel"},
            {"thinking": "payload-sentinel"},
            {
                "tool_calls": [
                    {
                        "function": {
                            "name": "counter",
                            "arguments": {"credential": "payload-sentinel"},
                        }
                    }
                ]
            },
        ],
    )
    @pytest.mark.parametrize("newline", [b"", b"\n"])
    async def should_retain_observed_evidence_on_capture_failure_without_replay(
        self, semantic, newline
    ):
        import json

        cause, captured, lifecycle = OSError("credential-sentinel"), [], []
        body = (
            json.dumps(
                {"done": True, "done_reason": "length", "message": semantic}
            ).encode()
            + newline
        )

        def capture(event):
            captured.append(event)
            if event.kind == "body":
                raise cause

        with scripted_http([(200, {"X-Secret": "credential-sentinel"}, body)]) as (
            host,
            requests,
        ):
            events = await collect(
                OllamaGateway(
                    host=host,
                    headers={"Authorization": "credential-sentinel"},
                    recovery_policy=RecoveryPolicy(
                        max_attempts=3,
                        admission=allow,
                        wire_observer=capture,
                        observer=lifecycle.append,
                    ),
                )
            )
        assert len(requests) == 1
        assert [event.kind for event in events] == ["failed"]
        error = events[-1].error
        failure = error.report.final_failure
        assert failure.progress.semantic
        assert (
            failure.progress.delivered_content
            == failure.progress.delivered_reasoning
            == 0
        )
        assert (
            failure.progress.delivered_tool_fragments
            == failure.progress.delivered_tool_calls
            == 0
        )
        assert failure.reason == "capture_failed"
        assert failure.inspect_cause() is cause
        assert error.inspect_cause() is cause
        assert failure.inspect_response() == body
        assert dict(error.inspect_headers())["x-secret"] == "credential-sentinel"
        assert [event.kind for event in captured] == ["request", "headers", "body"]
        safe = (
            str(error)
            + repr(error)
            + error.report.model_dump_json()
            + "".join(
                str(event) + repr(event) + event.model_dump_json()
                for event in events + lifecycle
            )
        )
        assert "payload-sentinel" not in safe
        assert "credential-sentinel" not in safe

    async def should_hide_provider_metadata_echoes_without_losing_explicit_evidence(
        self,
    ):
        body = ndjson(
            model="credential-sentinel",
            done=True,
            done_reason="payload-sentinel",
            message={},
            eval_count=0,
        )
        lifecycle = []
        with scripted_http([(200, {"X-Request-ID": "credential-sentinel"}, body)]) as (
            host,
            requests,
        ):
            events = await collect(
                OllamaGateway(
                    host=host, recovery_policy=RecoveryPolicy(observer=lifecycle.append)
                )
            )
        assert len(requests) == 1
        assert events[1].metrics.provider_model == "credential-sentinel"
        assert events[1].metrics.finish_reason == "payload-sentinel"
        assert events[-1].error.inspect_response() == body
        assert events[-1].report.final_failure.provider_request_id is None
        safe = "".join(
            str(event) + repr(event) + event.model_dump_json()
            for event in events + lifecycle
        )
        assert "credential-sentinel" not in safe
        assert "payload-sentinel" not in safe

    async def should_classify_provider_errors_without_exposing_body_text(self):
        body = ndjson(error="credential-sentinel")
        with scripted_http([(200, {}, body)]) as (host, requests):
            events = await collect(
                OllamaGateway(
                    host=host,
                    recovery_policy=RecoveryPolicy(max_attempts=3, admission=allow),
                )
            )
        assert len(requests) == 1
        failure = events[-1].report.final_failure
        assert failure.category == "provider_response"
        assert failure.reason == "provider_error"
        assert failure.inspect_response() == body
        assert "credential-sentinel" not in failure.model_dump_json()

    @pytest.mark.parametrize("kind,count", [("request", 0), ("headers", 1)])
    async def should_capture_failures_before_semantics_with_truthful_wire_counts(
        self, kind, count
    ):
        cause = OSError("secret")

        def capture(event):
            if event.kind == kind:
                raise cause

        with scripted_http([(200, {}, frame("answer") + b"\n")]) as (host, requests):
            events = await collect(
                OllamaGateway(
                    host=host,
                    recovery_policy=RecoveryPolicy(
                        max_attempts=3, admission=allow, wire_observer=capture
                    ),
                )
            )
        assert len(requests) == count
        assert events[-1].identity.wire_attempt == count
        assert len(events[-1].report.history) == count
        assert events[-1].error.inspect_cause() is cause
        assert events[-1].outcome.value == "interrupted"

    async def should_fail_when_success_observer_raises_without_delivering_completion(
        self,
    ):
        cause = OSError("secret")

        def observe(event):
            if event.transition == "attempt_succeeded":
                raise cause

        with scripted_http([(200, {}, frame("") + b"\n")]) as (host, requests):
            events = await collect(
                OllamaGateway(
                    host=host, recovery_policy=RecoveryPolicy(observer=observe)
                )
            )
        assert len(requests) == 1
        assert [event.kind for event in events] == ["progress", "metrics", "failed"]
        assert events[-1].error.inspect_cause() is cause
        assert events[-1].report.final_failure.reason == "observer_failed"

    async def should_preserve_native_streaming_tool_argument_types(self):
        tool = {
            "id": "call-id",
            "function": {
                "name": "counter",
                "arguments": {"count": 2, "nested": {"ok": True}},
            },
        }
        with scripted_http([(200, {}, frame("", tool_calls=[tool]) + b"\n")]) as (
            host,
            requests,
        ):
            events = await collect(
                OllamaGateway(host=host, recovery_policy=RecoveryPolicy())
            )
        assert len(requests) == 1
        response = events[-1].response
        assert response.tool_calls[0].arguments == {"count": 2, "nested": {"ok": True}}
        assert response.tool_calls[0].id == "call-id"
        assert events[-1].report.progress.completed_tool_calls == 1
        assert events[-1].report.progress.delivered_tool_calls == 1

    async def should_record_capture_failure_before_cancel_when_both_occur(self):
        from mojentic.llm.recovery import RecoveryCall

        call, cause, lifecycle = RecoveryCall(), OSError("capture-secret"), []

        def capture(event):
            if event.kind == "body":
                call.cancel()
                raise cause

        with scripted_http([(200, {}, frame("é") + b"\n")]) as (host, requests):
            events = await collect(
                OllamaGateway(
                    host=host,
                    recovery_policy=RecoveryPolicy(
                        wire_observer=capture, observer=lifecycle.append
                    ),
                ),
                call,
            )
        assert len(requests) == 1
        assert [event.kind for event in events] == ["failed"]
        assert events[-1].outcome.value == "cancelled"
        assert events[-1].report.history[0].reason == "capture_failed"
        assert events[-1].report.history[0].inspect_cause() is cause
        assert events[-1].report.history[0].progress.observed_content
        assert events[-1].report.history[0].progress.delivered_content == 0
        assert [event.transition for event in lifecycle] == [
            "attempt_started",
            "attempt_failed",
            "cancelled",
        ]

    async def should_reject_expired_budget_before_dispatch(self):
        with scripted_http([]) as (host, requests):
            events = await collect(
                OllamaGateway(
                    host=host,
                    recovery_policy=RecoveryPolicy(deadline=0, monotonic=lambda: 1),
                )
            )
        assert requests == []
        assert events[-1].outcome.value == "budget_exhausted"
        assert events[-1].identity.wire_attempt == 0
        assert events[-1].report.history == ()

    async def should_close_local_resources_when_iterator_is_closed(self):
        lifecycle = []
        with scripted_http([(200, {}, frame("partial") + b"\n")]) as (host, requests):
            stream = OllamaGateway(
                host=host, recovery_policy=RecoveryPolicy(observer=lifecycle.append)
            ).complete_stream_with_recovery(
                model="test", messages=[LLMMessage(content="query")]
            )
            event = await anext(stream)
            assert event.kind == "progress"
            await stream.aclose()
        assert len(requests) == 1
        assert [event.transition for event in lifecycle] == [
            "attempt_started",
            "attempt_failed",
            "cancelled",
        ]

    async def should_reset_frame_indices_after_nonsemantic_progress_retry(self):
        keepalive = ndjson(done=False, message={})
        with scripted_http(
            [
                (200, {"Content-Length": str(len(keepalive) + 10)}, keepalive),
                (200, {}, frame("answer") + b"\n"),
            ]
        ) as (host, requests):
            events = await collect(
                OllamaGateway(
                    host=host,
                    recovery_policy=RecoveryPolicy(
                        max_attempts=2, base_delay=0, admission=allow
                    ),
                )
            )
        assert len(requests) == 2
        progress = [event for event in events if event.kind == "progress"]
        assert [event.frame_index for event in progress] == [1, 1]
        assert [event.identity.wire_attempt for event in progress] == [1, 2]
        assert progress[0].frame_progress.content_bytes == 0
        assert events[-1].report.history[0].progress.raw_bytes == len(keepalive)
        assert not events[-1].report.history[0].progress.semantic

    @pytest.mark.parametrize("prefix,completed", [(b"", 1), (b"invalid\n", 0)])
    async def should_retain_valid_completed_tool_evidence_when_terminal_capture_fails(
        self, prefix, completed
    ):
        cause = OSError("capture-secret")

        def capture(event):
            if event.kind == "body":
                raise cause

        body = prefix + (
            frame("", tool_calls=[{"function": {"name": "counter", "arguments": {}}}])
            + b"\n"
        )
        with scripted_http([(200, {}, body)]) as (host, requests):
            events = await collect(
                OllamaGateway(
                    host=host,
                    recovery_policy=RecoveryPolicy(
                        max_attempts=3, admission=allow, wire_observer=capture
                    ),
                )
            )
        assert len(requests) == 1
        assert [event.kind for event in events] == ["failed"]
        assert events[-1].report.final_failure.reason == "capture_failed"
        assert events[-1].error.inspect_cause() is cause
        assert events[-1].progress.completed_tool_calls == completed
        assert events[-1].progress.observed_tool_fragments == 1
        assert (
            events[-1].progress.delivered_tool_fragments
            == events[-1].progress.delivered_tool_calls
            == 0
        )
