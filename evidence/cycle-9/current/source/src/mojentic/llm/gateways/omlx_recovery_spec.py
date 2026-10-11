"""Public oMLX recovery assertions at the loopback HTTP boundary."""

import asyncio
import json
import threading

import httpx
import pytest
from pydantic import BaseModel

from mojentic.llm.chat_session import ChatSession
from mojentic.llm.completion_config import CompletionConfig
from mojentic.llm.gateways.models import LLMMessage, LLMToolCall, MessageRole
from mojentic.llm.gateways.ollama_recovery_spec import scripted_http
from mojentic.llm.gateways.omlx import OMLXGateway
from mojentic.llm.gateways.tokenizer_gateway import TokenizerGateway
from mojentic.llm.llm_broker import LLMBroker
from mojentic.llm.recovery import RecoveryCall, RecoveryError, RecoveryPolicy
from mojentic.llm.tools.llm_tool import LLMTool


class DescribeOMLXRecovery:
    def should_observe_content_before_failing_capture_without_replay(self):
        body = b'data: {"choices":[{"delta":{"content":"secret"}}]}\n\n'
        cause = OSError("secret capture failure")
        lifecycle = []

        def capture(event):
            if event.kind == "body":
                raise cause

        with scripted_http([(200, {}, body)]) as (host, requests):
            gateway = OMLXGateway(
                host=host,
                recovery_policy=RecoveryPolicy(
                    max_attempts=3, wire_observer=capture, observer=lifecycle.append
                ),
            )
            with pytest.raises(RecoveryError) as caught:
                list(
                    gateway.complete_stream(
                        model="test", messages=[LLMMessage(content="payload")]
                    )
                )

        failure = caught.value.report.final_failure
        assert len(requests) == 1
        assert failure.provider == "omlx"
        assert failure.progress.observed_content
        assert failure.progress.delivered_content == 0
        assert failure.reason == "capture_failed"
        assert failure.inspect_cause() is cause
        assert failure.inspect_response() == body
        assert [event.transition for event in lifecycle] == [
            "attempt_started",
            "attempt_failed",
            "interrupted",
        ]


class Result(BaseModel):
    answer: str


def completion(content="answer", **message):
    return json.dumps(
        {
            "model": "actual-model",
            "usage": {"prompt_tokens": 2, "completion_tokens": 3, "total_tokens": 5},
            "choices": [
                {
                    "finish_reason": "length",
                    "message": {"role": "assistant", "content": content, **message},
                }
            ],
        },
        ensure_ascii=False,
    ).encode()


def sse(delta=None, finish=None, **fields):
    return (
        b"data: "
        + json.dumps(
            {"choices": [{"delta": delta or {}, "finish_reason": finish}], **fields},
            ensure_ascii=False,
        ).encode()
        + b"\n\n"
    )


def stream(content="answer"):
    return (
        sse(
            {"content": content, "reasoning_content": "native reason"},
            model="actual-model",
        )
        + sse(
            finish="stop",
            usage={"prompt_tokens": 2, "completion_tokens": 3, "total_tokens": 5},
        )
        + b"data: [DONE]\n\n"
    )


async def allow(context):
    return "allow"


async def reject(context):
    return "reject"


async def collect(gateway, **args):
    return [
        event
        async for event in gateway.complete_stream_with_recovery(
            model="test", messages=[LLMMessage(content="payload-sentinel")], **args
        )
    ]


async def invoke(gateway, operation):
    if operation == "streaming":
        events = await collect(gateway)
        if events[-1].error is not None:
            raise events[-1].error
        return events[-1].response
    return await gateway.complete_with_recovery(
        model="test",
        messages=[LLMMessage(content="payload-sentinel")],
        object_model={"ordinary": None, "structured": Result}[operation],
    )


@pytest.fixture
def broker_factory(mocker):
    def create(gateway):
        tokenizer = mocker.Mock(spec=TokenizerGateway)
        tokenizer.encode.return_value = []
        return LLMBroker("test", gateway=gateway, tokenizer=tokenizer)

    return create


@pytest.fixture
def counter_tool():
    class Counter(LLMTool):
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

    return Counter()


OPERATIONS = ["ordinary", "structured", "streaming"]


class DescribeOMLXWireRecovery:
    @pytest.mark.parametrize("operation", OPERATIONS)
    @pytest.mark.parametrize(
        "retry_after,state,delay",
        [
            ("2", "seconds", 2),
            ("Thu, 01 Jan 1970 00:00:03 GMT", "date", 3),
            ("invalid", "invalid", 0.5),
        ],
    )
    async def should_recover_503_with_stable_exact_semantic_bytes_and_lifecycle(
        self, operation, retry_after, state, delay, counter_tool
    ):
        captures, lifecycle, delays = [], [], []

        async def sleep(value):
            delays.append(value)

        messages = [
            LLMMessage(role=MessageRole.System, content="system"),
            LLMMessage(role=MessageRole.User, content="héllo"),
            LLMMessage(
                role=MessageRole.Assistant,
                content="prior",
                tool_calls=[LLMToolCall(id="old", name="counter", arguments={})],
            ),
            LLMMessage(
                role=MessageRole.Tool,
                content="result",
                tool_calls=[LLMToolCall(id="old", name="counter", arguments={})],
            ),
        ]
        config = CompletionConfig(
            temperature=0.25, max_tokens=17, reasoning_effort="high"
        )
        object_model = Result if operation == "structured" else None
        expected = {
            "model": "test",
            "messages": [
                {"role": "system", "content": "system"},
                {"role": "user", "content": "héllo"},
                {
                    "role": "assistant",
                    "content": "prior",
                    "tool_calls": [
                        {
                            "id": "old",
                            "type": "function",
                            "function": {"name": "counter", "arguments": "{}"},
                        }
                    ],
                },
                {"role": "tool", "content": "result", "tool_call_id": "old"},
            ],
            "temperature": 0.25,
            "max_tokens": 17,
            "reasoning_effort": "high",
            "tools": [
                {
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
            ],
        }
        expected_tools = expected.pop("tools")
        if operation == "structured":
            expected["response_format"] = {
                "type": "json_schema",
                "json_schema": {
                    "name": "response",
                    "schema": {
                        "properties": {"answer": {"title": "Answer", "type": "string"}},
                        "required": ["answer"],
                        "title": "Result",
                        "type": "object",
                    },
                },
            }
        expected["tools"] = expected_tools
        if operation == "streaming":
            expected |= {"stream": True, "stream_options": {"include_usage": True}}
        encoded = json.dumps(
            expected, ensure_ascii=False, separators=(",", ":"), allow_nan=False
        ).encode()
        success = (
            stream("é")
            if operation == "streaming"
            else completion('{"answer":"é"}', reasoning_content="native reason")
        )
        with scripted_http(
            [(503, {"Retry-After": retry_after}, b"busy"), (200, {}, success)]
        ) as (host, requests):
            gateway = OMLXGateway(
                host=host,
                api_key="credential-sentinel",
                recovery_policy=RecoveryPolicy(
                    max_attempts=2,
                    base_delay=1,
                    jitter=lambda ceiling: ceiling / 2,
                    wall=lambda: 0,
                    admission=allow,
                    sleeper=sleep,
                    observer=lifecycle.append,
                    wire_observer=captures.append,
                ),
            )
            args = {
                "model": "test",
                "messages": messages,
                "config": config,
                "tools": [counter_tool],
            }
            if operation == "streaming":
                events = [
                    event
                    async for event in gateway.complete_stream_with_recovery(**args)
                ]
                response = events[-1].response
                assert events[-1].kind == "completed"
                assert response.content == "é"
                assert response.recovery_report.progress.delivered_content == 2
            else:
                response = await gateway.complete_with_recovery(
                    **args, object_model=object_model
                )
                assert response.content == '{"answer":"é"}'
            assert [request[1] for request in requests] == [encoded, encoded]
            assert [request[0] for request in requests] == ["/v1/chat/completions"] * 2
            assert requests[0][2]["Authorization"] == "Bearer credential-sentinel"
        assert delays == [delay]
        assert response.thinking == "native reason"
        assert response.usage == {
            "prompt_tokens": 2,
            "completion_tokens": 3,
            "total_tokens": 5,
        }
        assert response.model == "actual-model"
        assert (
            response.finish_reason
            == {"streaming": "stop", "ordinary": "length", "structured": "length"}[
                operation
            ]
        )
        report = response.recovery_report
        assert report.identity.wire_attempt == 2
        assert report.history[0].provider == "omlx"
        assert report.history[0].retry_after.state == state
        assert report.history[0].identity.attempt_id != report.identity.attempt_id
        assert (
            report.history[0].identity.logical_request_id
            == report.identity.logical_request_id
        )
        assert [event.body for event in captures if event.kind == "request"] == [
            encoded,
            encoded,
        ]
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

    @pytest.mark.parametrize("operation", OPERATIONS)
    @pytest.mark.parametrize(
        "policy_args,outcome",
        [
            ({"delay_ceiling": 1}, "delay_ceiling"),
            ({"budget": 1}, "budget_exhausted"),
        ],
    )
    async def should_refuse_retry_after_outside_limits(
        self, operation, policy_args, outcome
    ):
        with scripted_http([(503, {"Retry-After": "2"}, b"private")]) as (
            host,
            requests,
        ):
            gateway = OMLXGateway(
                host=host,
                recovery_policy=RecoveryPolicy(
                    max_attempts=2, base_delay=0, admission=allow, **policy_args
                ),
            )
            with pytest.raises(RecoveryError) as caught:
                await invoke(gateway, operation)
        assert len(requests) == 1
        assert caught.value.report.outcome == outcome
        assert caught.value.report.final_failure.retry_after.delay == 2

    @pytest.mark.parametrize("operation", OPERATIONS)
    async def should_bound_504_exhaustion_without_success(self, operation):
        lifecycle = []
        with scripted_http([(504, {}, b"private")] * 3) as (host, requests):
            gateway = OMLXGateway(
                host=host,
                recovery_policy=RecoveryPolicy(
                    max_attempts=3,
                    base_delay=0,
                    admission=allow,
                    observer=lifecycle.append,
                ),
            )
            with pytest.raises(RecoveryError) as caught:
                await invoke(gateway, operation)
        assert len(requests) == 3
        assert caught.value.report.outcome == "attempts_exhausted"
        assert [f.http_status for f in caught.value.report.history] == [504, 504, 504]
        assert all(
            isinstance(caught.value.inspect_cause(i), httpx.HTTPStatusError)
            for i in range(3)
        )
        assert [event.transition for event in lifecycle][-2:] == [
            "attempt_failed",
            "exhausted",
        ]
        assert "attempt_succeeded" not in [event.transition for event in lifecycle]

    @pytest.mark.parametrize("operation", OPERATIONS)
    @pytest.mark.parametrize("status", [400, 401, 403])
    async def should_keep_truncated_permanent_status_even_with_transport_eligibility(
        self, operation, status
    ):
        with scripted_http(
            [
                (
                    status,
                    {"Content-Length": "100", "X-Request-ID": "credential-sentinel"},
                    b"partial",
                )
            ]
        ) as (host, requests):
            gateway = OMLXGateway(
                host=host,
                recovery_policy=RecoveryPolicy(
                    max_attempts=3,
                    retryable_categories=frozenset({"transport", "http"}),
                    retryable_statuses=frozenset({400, 401, 403}),
                    admission=allow,
                ),
            )
            with pytest.raises(RecoveryError) as caught:
                await invoke(gateway, operation)
        error = caught.value
        failure = error.report.final_failure
        assert len(requests) == 1
        assert failure.http_status == status
        assert failure.reason == "permanent"
        assert not failure.eligible
        assert failure.progress.raw_bytes == 7
        assert error.inspect_response() == b"partial"
        assert isinstance(error.inspect_cause(), httpx.RemoteProtocolError)
        assert ("x-request-id", "credential-sentinel") in error.inspect_headers()
        assert error.report.history == (failure,)

    @pytest.mark.parametrize("operation", OPERATIONS)
    @pytest.mark.parametrize(
        "admission,outcome,wire_count",
        [
            (None, "admission_required", 1),
            (reject, "admission_rejected", 1),
            (allow, "succeeded", 2),
        ],
    )
    async def should_require_admission_for_ambiguous_local_failure(
        self, operation, admission, outcome, wire_count
    ):
        success = (
            stream() if operation == "streaming" else completion('{"answer":"ok"}')
        )
        with scripted_http(
            [(200, {"Content-Length": "100"}, b""), (200, {}, success)]
        ) as (host, requests):
            gateway = OMLXGateway(
                host=host,
                recovery_policy=RecoveryPolicy(
                    max_attempts=2, base_delay=0, admission=admission
                ),
            )
            try:
                response = await invoke(gateway, operation)
                actual = response.recovery_report.outcome
            except RecoveryError as error:
                actual = error.report.outcome
        assert len(requests) == wire_count
        assert actual == outcome

    @pytest.mark.parametrize("operation", OPERATIONS)
    async def should_never_follow_redirects(self, operation):
        with (
            scripted_http([(307, {"Location": "/v1/chat/completions"}, b"")]) as (
                host,
                requests,
            ),
            pytest.raises(RecoveryError) as caught,
        ):
            await invoke(
                OMLXGateway(
                    host=host,
                    recovery_policy=RecoveryPolicy(max_attempts=3, admission=allow),
                ),
                operation,
            )
        assert len(requests) == 1
        assert caught.value.report.final_failure.http_status == 307


class DescribeOMLXStreamSafety:
    @pytest.mark.parametrize(
        "delta,field",
        [
            ({"content": "é"}, "observed_content"),
            ({"reasoning_content": "think"}, "observed_reasoning"),
            (
                {
                    "tool_calls": [
                        {
                            "index": 0,
                            "id": "call",
                            "function": {"name": "counter", "arguments": "{"},
                        }
                    ]
                },
                "observed_tool_fragments",
            ),
        ],
    )
    async def should_interrupt_observed_semantics_without_replay(self, delta, field):
        with scripted_http([(200, {}, sse(delta))]) as (host, requests):
            events = await collect(
                OMLXGateway(
                    host=host,
                    recovery_policy=RecoveryPolicy(max_attempts=3, admission=allow),
                )
            )
        assert len(requests) == 1
        failure = events[-1].report.final_failure
        assert getattr(failure.progress, field)
        assert events[-1].outcome.value == "interrupted"
        assert isinstance(events[-1].error.inspect_cause(), httpx.RemoteProtocolError)
        assert "completed" not in [event.kind for event in events]

    @pytest.mark.parametrize(
        "body", [b"data: {broken}\n\n", b'data: {"choices":[]}', b"data: [DONE]\n\n"]
    )
    async def should_reject_malformed_or_unfinished_sse_without_retry(self, body):
        with scripted_http([(200, {}, body)]) as (host, requests):
            events = await collect(
                OMLXGateway(
                    host=host,
                    recovery_policy=RecoveryPolicy(max_attempts=3, admission=allow),
                )
            )
        assert len(requests) == 1
        assert [event.kind for event in events] == ["failed"]
        assert events[-1].report.final_failure.category == "protocol"
        assert not events[-1].report.final_failure.eligible
        assert events[-1].error.inspect_response() == body

    async def should_require_admission_after_keepalive_and_reset_frame_indices(self):
        keepalive = sse(model="keepalive")
        with scripted_http([(200, {}, keepalive), (200, {}, stream("ok"))]) as (
            host,
            requests,
        ):
            events = await collect(
                OMLXGateway(
                    host=host,
                    recovery_policy=RecoveryPolicy(
                        max_attempts=2, base_delay=0, admission=allow
                    ),
                )
            )
        assert len(requests) == 2
        failure = events[-1].report.history[0]
        assert failure.progress.raw_bytes == len(keepalive)
        assert not failure.progress.semantic
        assert events[0].frame_index == 1
        assert events[0].identity.wire_attempt == 2
        assert events[-1].response.model == "actual-model"
        assert events[-1].response.content == "ok"

    @pytest.mark.parametrize(
        "finish,terminal", [("stop", "completed"), ("length", "failed")]
    )
    async def should_preserve_terminal_telemetry_and_reject_length(
        self, finish, terminal
    ):
        data = sse(
            finish=finish,
            model="actual-model",
            usage={"prompt_tokens": 7, "completion_tokens": 11},
        )
        with scripted_http([(200, {}, data + b"data: [DONE]\n\n")]) as (host, requests):
            events = await collect(
                OMLXGateway(
                    host=host,
                    recovery_policy=RecoveryPolicy(max_attempts=2, admission=allow),
                )
            )
        assert len(requests) == 1
        assert [event.kind for event in events] == [
            "metrics",
            "progress",
            "metrics",
            terminal,
        ]
        assert events[0].metrics.usage == {"prompt_tokens": 7, "completion_tokens": 11}
        assert events[2].metrics.finish_reason == finish
        assert events[2].metrics.provider_model == "actual-model"
        assert events[1].frame_progress.content_bytes == 0
        assert events[-1].progress.delivered_tool_calls == 0

    async def should_complete_fragmented_tools_once_after_safe_terminal_marker(self):
        data = sse(
            {
                "tool_calls": [
                    {
                        "index": 0,
                        "id": "call",
                        "function": {"name": "counter", "arguments": "{"},
                    }
                ]
            }
        )
        data += sse(
            {"tool_calls": [{"index": 0, "function": {"arguments": "}"}}]},
            finish="tool_calls",
        )
        data += b"data: [DONE]\n\n"
        with scripted_http([(200, {}, data)]) as (host, requests):
            events = await collect(
                OMLXGateway(host=host, recovery_policy=RecoveryPolicy())
            )
        assert len(requests) == 1
        assert events[-1].kind == "completed"
        assert events[-1].response.tool_calls == [
            LLMToolCall(id="call", name="counter", arguments={})
        ]
        assert events[-1].progress.observed_tool_fragments == 2
        assert events[-1].progress.delivered_tool_fragments == 2
        assert events[-1].progress.completed_tool_calls == 1
        assert events[-1].progress.delivered_tool_calls == 1


class DescribeOMLXPublicCallers:
    @pytest.mark.parametrize(
        "entrypoint",
        [
            "generate",
            "generate_response",
            "generate_object",
            "generate_stream",
            "send",
            "send_stream",
        ],
    )
    def should_recover_through_broker_and_session(self, entrypoint, broker_factory):
        streaming = entrypoint in {"generate_stream", "send_stream"}
        data = stream("ok") if streaming else completion('{"answer":"ok"}')
        with scripted_http([(503, {}, b"busy"), (200, {}, data)]) as (host, requests):
            broker = broker_factory(
                OMLXGateway(
                    host=host,
                    recovery_policy=RecoveryPolicy(
                        max_attempts=2, base_delay=0, admission=allow
                    ),
                )
            )
            messages = [LLMMessage(content="payload")]
            session = ChatSession(broker, tokenizer_gateway=broker.tokenizer)
            actions = {
                "generate": lambda: broker.generate(messages),
                "generate_response": lambda: broker.generate_response(messages).content,
                "generate_object": lambda: (
                    broker.generate_object(messages, Result).answer
                ),
                "generate_stream": lambda: "".join(broker.generate_stream(messages)),
                "send": lambda: session.send("payload"),
                "send_stream": lambda: "".join(session.send_stream("payload")),
            }
            result = actions[entrypoint]()
        assert result == (
            "ok" if streaming or entrypoint == "generate_object" else '{"answer":"ok"}'
        )
        assert len(requests) == 2
        assert requests[0][1] == requests[1][1]

    @pytest.mark.parametrize(
        "entrypoint", ["generate", "generate_stream", "send", "send_stream"]
    )
    def should_execute_completed_tool_once_before_typed_subsequent_failure(
        self, entrypoint, broker_factory, counter_tool
    ):
        streaming = entrypoint in {"generate_stream", "send_stream"}
        call = {"id": "call", "function": {"name": "counter", "arguments": "{}"}}
        data = completion("", tool_calls=[call])
        if streaming:
            data = (
                sse({"tool_calls": [call | {"index": 0}]}, finish="tool_calls")
                + b"data: [DONE]\n\n"
            )
        lifecycle = []
        with scripted_http(
            [(200, {}, data), (504, {}, b"private"), (504, {}, b"private")]
        ) as (host, requests):
            broker = broker_factory(
                OMLXGateway(
                    host=host,
                    recovery_policy=RecoveryPolicy(
                        max_attempts=2,
                        base_delay=0,
                        admission=allow,
                        observer=lifecycle.append,
                    ),
                )
            )
            config = CompletionConfig(max_tool_iterations=2)
            messages = [LLMMessage(content="payload")]
            session = ChatSession(
                broker,
                tools=[counter_tool],
                config=config,
                tokenizer_gateway=broker.tokenizer,
            )
            actions = {
                "generate": lambda: broker.generate(
                    messages, tools=[counter_tool], config=config
                ),
                "generate_response": lambda: broker.generate_response(
                    messages, tools=[counter_tool], config=config
                ),
                "generate_stream": lambda: list(
                    broker.generate_stream(
                        messages, tools=[counter_tool], config=config
                    )
                ),
                "send": lambda: session.send("payload"),
                "send_stream": lambda: list(session.send_stream("payload")),
            }
            with pytest.raises(RecoveryError) as caught:
                actions[entrypoint]()
        assert counter_tool.calls == [{}]
        assert len(requests) == 3
        assert requests[1][1] == requests[2][1]
        payload = json.loads(requests[1][1])
        assert payload["messages"][-1] == {
            "role": "tool",
            "content": '"tool result"',
            "tool_call_id": "call",
        }
        assert config.max_tool_iterations == 2
        assert caught.value.report.outcome == "attempts_exhausted"
        assert isinstance(caught.value.inspect_cause(), httpx.HTTPStatusError)
        starts = [
            event.identity
            for event in lifecycle
            if event.transition == "attempt_started"
        ]
        assert [identity.wire_attempt for identity in starts] == [1, 1, 2]
        assert (
            starts[0].logical_request_id
            != starts[1].logical_request_id
            == starts[2].logical_request_id
        )

    def should_leave_raw_event_api_single_request_with_recovery_configured(
        self, broker_factory
    ):
        with scripted_http([(503, {}, b"private")]) as (host, requests):
            broker = broker_factory(
                OMLXGateway(
                    host=host,
                    recovery_policy=RecoveryPolicy(max_attempts=3, admission=allow),
                )
            )
            events = list(
                broker.generate_stream_events([LLMMessage(content="payload")])
            )
        assert len(requests) == 1
        assert len(events) == 1
        assert events[-1].type == "error"


class DescribeOMLXCancellation:
    @pytest.mark.parametrize("operation", OPERATIONS)
    @pytest.mark.parametrize("phase", ["admission", "backoff"])
    async def should_cancel_pending_admission_and_backoff_without_a_new_request(
        self, operation, phase
    ):
        entered, closed = asyncio.Event(), asyncio.Event()
        lifecycle, call = [], RecoveryCall()

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
        with scripted_http([(504, {}, b"private")]) as (host, requests):
            gateway = OMLXGateway(host=host, recovery_call=call, recovery_policy=policy)
            task = asyncio.create_task(invoke(gateway, operation))
            await asyncio.wait_for(entered.wait(), 2)
            assert len(requests) == 1
            assert not task.done()
            call.cancel()
            with pytest.raises(RecoveryError) as caught:
                await asyncio.wait_for(task, 2)
        assert closed.is_set()
        assert len(requests) == 1
        assert caught.value.report.outcome == "cancelled"
        assert caught.value.report.history[0].http_status == 504
        assert isinstance(caught.value.inspect_cause(0), httpx.HTTPStatusError)
        assert isinstance(caught.value.inspect_cause(), asyncio.CancelledError)
        transitions = [event.transition for event in lifecycle]
        assert transitions.count("attempt_failed") == 1
        assert transitions.count("cancelled") == 1
        assert transitions.index("attempt_failed") < transitions.index("cancelled")
        assert "attempt_succeeded" not in transitions

    @pytest.mark.parametrize("operation", OPERATIONS)
    async def should_leave_admission_pending_until_explicit_allow(self, operation):
        entered, release = asyncio.Event(), asyncio.Event()

        async def admission(context):
            assert context.next_attempt == 2
            assert context.previous_identity == context.failure.identity
            entered.set()
            await release.wait()
            return "allow"

        data = stream() if operation == "streaming" else completion('{"answer":"ok"}')
        with scripted_http([(503, {}, b"busy"), (200, {}, data)]) as (host, requests):
            gateway = OMLXGateway(
                host=host,
                recovery_policy=RecoveryPolicy(
                    max_attempts=2, base_delay=0, admission=admission
                ),
            )
            task = asyncio.create_task(invoke(gateway, operation))
            await asyncio.wait_for(entered.wait(), 2)
            assert len(requests) == 1
            assert not task.done()
            release.set()
            result = await asyncio.wait_for(task, 2)
        assert len(requests) == 2
        assert result.recovery_report.outcome == "succeeded"

    @pytest.mark.parametrize(
        "finish,category", [("stop", "cancellation"), ("length", "protocol")]
    )
    @pytest.mark.parametrize("consumed", [1, 2])
    async def should_cancel_while_terminal_telemetry_consumption_is_paused(
        self, finish, category, consumed
    ):
        call, lifecycle, cancelled = RecoveryCall(), [], threading.Event()

        def observe(event):
            lifecycle.append(event)
            if event.transition == "cancelled":
                cancelled.set()

        data = (
            sse(finish=finish, usage={"prompt_tokens": 2, "completion_tokens": 3})
            + b"data: [DONE]\n\n"
        )
        with scripted_http([(200, {}, data)]) as (host, requests):
            gateway = OMLXGateway(
                host=host, recovery_policy=RecoveryPolicy(observer=observe)
            )
            iterator = gateway.complete_stream_with_recovery(
                model="test", messages=[], call=call
            )
            received = [await anext(iterator) for _ in range(consumed)]
            call.cancel()
            assert await asyncio.wait_for(asyncio.to_thread(cancelled.wait, 1), 2)
            remaining = [event async for event in iterator]
        assert len(requests) == 1
        assert all(event.kind in {"progress", "metrics"} for event in received)
        assert remaining[-1].kind == "failed"
        assert remaining[-1].outcome.value == "cancelled"
        assert remaining[-1].report.history[0].category == category
        assert remaining[-1].report.final_failure.category == "cancellation"
        transitions = [event.transition for event in lifecycle]
        assert transitions.count("attempt_failed") == 1
        assert transitions.count("cancelled") == 1
        assert "attempt_succeeded" not in transitions

    @pytest.mark.parametrize("operation", OPERATIONS)
    async def should_cancel_active_request_and_close_local_socket(self, operation):
        from contextlib import contextmanager
        from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

        started, closed = threading.Event(), threading.Event()
        requests = []

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                requests.append(self.rfile.read(int(self.headers["Content-Length"])))
                started.set()
                self.connection.settimeout(2)
                assert self.connection.recv(1) == b""
                closed.set()

            def log_message(self, *args):
                pass

        @contextmanager
        def server():
            http = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
            thread = threading.Thread(
                target=lambda: http.serve_forever(poll_interval=0.01), daemon=True
            )
            thread.start()
            try:
                yield f"http://127.0.0.1:{http.server_port}"
            finally:
                http.shutdown()
                http.server_close()
                thread.join()

        call, lifecycle = RecoveryCall(), []
        with server() as host:
            gateway = OMLXGateway(
                host=host,
                recovery_call=call,
                recovery_policy=RecoveryPolicy(observer=lifecycle.append),
            )
            task = asyncio.create_task(invoke(gateway, operation))
            assert await asyncio.wait_for(asyncio.to_thread(started.wait, 1), 2)
            call.cancel()
            with pytest.raises(RecoveryError) as caught:
                await asyncio.wait_for(task, 1)
            assert await asyncio.wait_for(asyncio.to_thread(closed.wait, 1), 2)
        assert len(requests) == 1
        assert isinstance(caught.value.inspect_cause(), asyncio.CancelledError)
        assert caught.value.report.identity.wire_attempt == 1
        assert [event.transition for event in lifecycle] == [
            "attempt_started",
            "attempt_failed",
            "cancelled",
        ]


class DescribeOMLXPrivacyAndValidation:
    @pytest.mark.parametrize("operation", OPERATIONS)
    async def should_keep_echoed_secrets_out_of_safe_errors_events_and_logs(
        self, operation, caplog
    ):
        secret = "credential-payload-echo-sentinel"
        captures, lifecycle = [], []
        headers = {"X-Request-ID": secret, "Warning": secret}
        data = json.dumps({"error": {"code": secret, "message": secret}}).encode()
        with scripted_http([(503, headers, data)]) as (host, requests):
            gateway = OMLXGateway(
                host=host,
                api_key=secret,
                recovery_policy=RecoveryPolicy(
                    observer=lifecycle.append, wire_observer=captures.append
                ),
            )
            with pytest.raises(RecoveryError) as caught:
                await invoke(gateway, operation)
        error = caught.value
        assert len(requests) == 1
        assert secret not in str(error)
        assert secret not in repr(error.report)
        assert secret not in error.report.model_dump_json()
        assert secret not in "".join(event.model_dump_json() for event in lifecycle)
        assert secret not in caplog.text
        assert error.inspect_response() == data
        assert ("warning", secret) in error.inspect_headers()
        request = next(event for event in captures if event.kind == "request")
        assert ("authorization", f"Bearer {secret}") in request.headers
        assert request.body == requests[0][1]

    async def should_preserve_full_actual_provider_usage_without_serializing_untrusted_keys(
        self,
    ):
        usage = {
            "prompt_tokens_details": {"cached_tokens": 1},
            "time_to_first_token": 0.12,
            "total_time": 0.5,
            "tokens_per_second": 2.3,
            "credential-sentinel": 1,
        }
        data = stream("ok").replace(
            b"data: [DONE]",
            b"data: "
            + json.dumps({"choices": [], "usage": usage}).encode()
            + b"\n\ndata: [DONE]",
        )
        with scripted_http([(200, {}, data)]) as (host, requests):
            events = await collect(
                OMLXGateway(host=host, recovery_policy=RecoveryPolicy())
            )
        assert len(requests) == 1
        assert events[-1].response.usage == usage
        metrics = [event.metrics for event in events if event.kind == "metrics"]
        assert metrics[-1].usage == usage
        assert "credential-sentinel" not in "".join(
            event.model_dump_json() for event in events
        )
        assert "credential-sentinel" not in repr(metrics[-1])

    @pytest.mark.parametrize(
        "payload",
        [
            {"choices": [1]},
            {"choices": [{"message": {"content": 42}}]},
            {
                "choices": [
                    {
                        "message": {
                            "tool_calls": [
                                {"function": {"name": "", "arguments": "{}"}}
                            ]
                        }
                    }
                ]
            },
        ],
    )
    async def should_propagate_typed_invalid_completion_without_another_request(
        self, payload
    ):
        with scripted_http([(200, {}, json.dumps(payload).encode())]) as (
            host,
            requests,
        ):
            gateway = OMLXGateway(
                host=host,
                recovery_policy=RecoveryPolicy(max_attempts=3, admission=allow),
            )
            with pytest.raises(RecoveryError) as caught:
                await invoke(gateway, "ordinary")
        assert len(requests) == 1
        assert caught.value.report.final_failure.category == "protocol"
        assert len(caught.value.report.history) == 1

    def should_validate_schema_and_preserve_format_warning(self):
        with scripted_http(
            [(200, {"Warning": "format fallback"}, completion('{"answer":"ok"}'))]
        ) as (host, requests):
            response = OMLXGateway(
                host=host, recovery_policy=RecoveryPolicy()
            ).complete(model="test", messages=[], object_model=Result)
        assert len(requests) == 1
        assert response.object == Result(answer="ok")
        assert response.metadata["response_format_warning"] == "format fallback"

    def should_reject_invalid_schema_with_typed_cause(self):
        with (
            scripted_http([(200, {}, completion('{"wrong":1}'))]) as (host, requests),
            pytest.raises(RecoveryError) as caught,
        ):
            OMLXGateway(
                host=host,
                recovery_policy=RecoveryPolicy(max_attempts=3, admission=allow),
            ).complete(model="test", messages=[], object_model=Result)
        assert len(requests) == 1
        assert isinstance(caught.value.inspect_cause(), ValueError)
        assert caught.value.report.final_failure.operation == "structured"


class DescribeOMLXCaptureEvidence:
    @pytest.mark.parametrize("operation", OPERATIONS)
    @pytest.mark.parametrize(
        "channel,field",
        [
            ("content", "observed_content"),
            ("reasoning_content", "observed_reasoning"),
            ("tool_calls", "observed_tool_fragments"),
        ],
    )
    async def should_retain_all_observed_channels_before_capture_failure(
        self, operation, channel, field
    ):
        cause, captures, lifecycle = OSError("private hook failure"), [], []
        values = {
            "content": "é",
            "reasoning_content": "reason",
            "tool_calls": [
                {
                    "index": 0,
                    "id": "call",
                    "function": {"name": "counter", "arguments": "{}"},
                }
            ],
        }
        message = {channel: values[channel]}
        data = (
            sse(message)
            if operation == "streaming"
            else completion(**({"content": None} | message))
        )
        if channel == "content" and operation != "streaming":
            data = completion("é")

        def capture(event):
            captures.append(event)
            if event.kind == "body":
                raise cause

        with scripted_http([(200, {}, data)]) as (host, requests):
            gateway = OMLXGateway(
                host=host,
                recovery_policy=RecoveryPolicy(
                    max_attempts=3,
                    admission=allow,
                    wire_observer=capture,
                    observer=lifecycle.append,
                ),
            )
            with pytest.raises(RecoveryError) as caught:
                await invoke(gateway, operation)
        failure = caught.value.report.final_failure
        assert len(requests) == 1
        assert getattr(failure.progress, field)
        assert failure.progress.delivered_content == 0
        assert failure.progress.delivered_reasoning == 0
        assert failure.progress.delivered_tool_fragments == 0
        assert failure.progress.delivered_tool_calls == 0
        assert (
            failure.reason
            == {
                "ordinary": "semantic_output",
                "structured": "semantic_output",
                "streaming": "capture_failed",
            }[operation]
        )
        assert caught.value.inspect_response() == data
        assert caught.value.inspect_cause() is cause
        assert [event.transition for event in lifecycle] == [
            "attempt_started",
            "attempt_failed",
            "interrupted",
        ]

    @pytest.mark.parametrize(
        "fixture_name", ["stream_thinking.sse", "stream_tool_call.sse"]
    )
    async def should_preserve_actual_fixture_usage_and_supported_thinking_and_tools(
        self, fixture_name
    ):
        from pathlib import Path

        data = (
            Path(__file__)
            .with_name("fixtures")
            .joinpath("omlx", fixture_name)
            .read_bytes()
        )
        frames = [
            json.loads(line[6:])
            for line in data.splitlines()
            if line.startswith(b"data: {")
        ]
        expected_usage = next(
            frame["usage"] for frame in frames if frame.get("usage") is not None
        )
        with scripted_http([(200, {}, data)]) as (host, requests):
            events = await collect(
                OMLXGateway(host=host, recovery_policy=RecoveryPolicy())
            )
        assert len(requests) == 1
        assert events[-1].kind == "completed"
        assert events[-1].response.usage == expected_usage
        assert [event.metrics.usage for event in events if event.kind == "metrics"][
            -1
        ] == expected_usage
        assert events[-1].progress.raw_bytes == len(data)


class DescribeOMLXMalformedToolFields:
    @pytest.mark.parametrize("operation", OPERATIONS)
    @pytest.mark.parametrize("value", [{}, "", 0, False])
    async def should_reject_false_non_array_tool_fields(self, operation, value):
        ordinary = completion("safe content", tool_calls=value)
        data = {
            "ordinary": ordinary,
            "structured": ordinary,
            "streaming": sse(
                {"content": "safe content", "tool_calls": value}, finish="stop"
            )
            + b"data: [DONE]\n\n",
        }[operation]
        with scripted_http([(200, {}, data)]) as (host, requests):
            gateway = OMLXGateway(
                host=host,
                recovery_policy=RecoveryPolicy(max_attempts=3, admission=allow),
            )
            with pytest.raises(RecoveryError) as caught:
                await invoke(gateway, operation)
        assert len(requests) == 1
        assert caught.value.report.final_failure.category == "protocol"
        assert isinstance(caught.value.inspect_cause(), TypeError)

    @pytest.mark.parametrize("value", ["", 0, False])
    async def should_reject_false_non_object_tool_functions(self, value):
        data = (
            sse({"tool_calls": [{"index": 0, "function": value}]}, finish="tool_calls")
            + b"data: [DONE]\n\n"
        )
        with scripted_http([(200, {}, data)]) as (host, requests):
            events = await collect(
                OMLXGateway(
                    host=host,
                    recovery_policy=RecoveryPolicy(max_attempts=3, admission=allow),
                )
            )
        assert len(requests) == 1
        assert events[-1].kind == "failed"
        assert isinstance(events[-1].error.inspect_cause(), TypeError)
        assert events[-1].progress.delivered_tool_calls == 0


class DescribeOMLXPreparationPrivacy:
    @pytest.mark.parametrize("operation", ["ordinary", "streaming"])
    def should_keep_invalid_control_errors_typed_and_private_before_dispatch(
        self, operation
    ):
        with scripted_http([]) as (host, requests):
            gateway = OMLXGateway(host=host, recovery_policy=RecoveryPolicy())
            args = {
                "model": "test",
                "messages": [],
                "temperature": "credential-payload-sentinel",
            }
            actions = {
                "ordinary": lambda: gateway.complete(**args),
                "streaming": lambda: list(gateway.complete_stream(**args)),
            }
            with pytest.raises(RecoveryError) as caught:
                actions[operation]()
        assert requests == []
        assert caught.value.report.identity.wire_attempt == 0
        assert caught.value.report.identity.attempt_id is None
        assert caught.value.report.history == ()
        assert caught.value.report.final_failure.acceptance == "no"
        assert caught.value.report.final_failure.provider == "omlx"
        assert "credential-payload-sentinel" not in str(caught.value)
        assert (
            "credential-payload-sentinel" not in caught.value.report.model_dump_json()
        )
        assert isinstance(caught.value.inspect_cause(), ValueError)
