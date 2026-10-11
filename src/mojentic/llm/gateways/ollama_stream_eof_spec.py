"""EOF classification contracts through real public Ollama HTTP streams."""

import json
import os
from pathlib import Path

import httpx
import pytest

from mojentic.llm.gateways import ollama_stream_recovery_spec as stream_specs
from mojentic.llm.gateways.models import LLMMessage
from mojentic.llm.gateways.ollama import OllamaGateway
from mojentic.llm.gateways.ollama_recovery_spec import frame, scripted_http
from mojentic.llm.gateways.ollama_stream_recovery_spec import allow, collect, ndjson
from mojentic.llm.recovery import RecoveryError, RecoveryPolicy


@pytest.fixture
def counter_tool():
    return stream_specs.counter_tool.__wrapped__()


@pytest.fixture
def captures(request):
    events = []
    yield events
    destination = os.environ.get("MOJENTIC_EOF_EVIDENCE")
    if destination:
        with Path(destination).open("a") as log:
            log.write(
                json.dumps(
                    {
                        "test": request.node.nodeid,
                        "captures": [
                            event.model_dump(mode="json")
                            | {
                                "body_hex": event.body.hex(),
                                "headers": event.headers,
                                "url": event.url,
                                "method": event.method,
                                "identity": event.identity.model_dump(mode="json"),
                            }
                            for event in events
                        ],
                    }
                )
                + "\n"
            )


class DescribeOllamaStreamEOF:
    @pytest.mark.parametrize("extra_bytes", [0, 10])
    async def should_reject_unfinished_frame_after_complete_keepalive(
        self, extra_bytes, captures
    ):
        keepalive = ndjson(done=False, message={})
        body = keepalive + b'{"message":{"content":"unfinished'
        with scripted_http(
            [
                (200, {"Content-Length": str(len(body) + extra_bytes)}, body),
                (200, {}, frame("retry") + b"\n"),
            ]
        ) as (host, requests):
            events = await collect(
                OllamaGateway(
                    host=host,
                    recovery_policy=RecoveryPolicy(
                        max_attempts=2,
                        base_delay=0,
                        admission=allow,
                        wire_observer=captures.append,
                    ),
                )
            )

        assert len(requests) == 1
        assert [event.kind for event in events] == ["progress", "failed"]
        assert events[0].frame_index == 1
        failure = events[-1].report.final_failure
        assert failure.category == "protocol"
        assert not failure.eligible
        assert not failure.progress.semantic
        assert failure.inspect_response() == body
        assert len(events[-1].report.history) == 1
        assert failure.progress.raw_bytes == len(body)
        assert failure.identity == events[0].identity

    @pytest.mark.parametrize(
        "extra_bytes,cause_type", [(0, ValueError), (10, httpx.RemoteProtocolError)]
    )
    @pytest.mark.parametrize(
        "body,content,reasoning,tools,completed",
        [
            (b'{"done":', False, False, 0, 0),
            (frame("unfinished"), True, False, 0, 0),
            (
                frame(
                    "",
                    thinking="é",
                    tool_calls=[{"function": {"name": "counter", "arguments": {}}}],
                ),
                False,
                True,
                1,
                1,
            ),
        ],
    )
    async def should_block_unfinished_frame_even_with_admission(
        self,
        extra_bytes,
        cause_type,
        body,
        content,
        reasoning,
        tools,
        completed,
        captures,
    ):
        admissions, lifecycle = [], []

        async def admit(context):
            admissions.append(context)
            return "allow"

        headers = {
            "Content-Length": str(len(body) + extra_bytes),
            "X-Evidence": "eof-secret",
        }
        with scripted_http(
            [(200, headers, body), (200, {}, frame("retried") + b"\n")]
        ) as (host, requests):
            events = await collect(
                OllamaGateway(
                    host=host,
                    recovery_policy=RecoveryPolicy(
                        max_attempts=2,
                        base_delay=0,
                        admission=admit,
                        wire_observer=captures.append,
                        observer=lifecycle.append,
                    ),
                )
            )

        assert len(requests) == 1
        assert admissions == []
        assert [event.kind for event in events] == ["failed"]
        assert events[-1].report.final_failure.category == "protocol"
        assert not events[-1].report.final_failure.eligible
        failure = events[-1].report.final_failure
        assert failure.inspect_response() == body
        assert dict(failure.inspect_headers())["x-evidence"] == "eof-secret"
        assert isinstance(failure.inspect_cause(), cause_type)
        assert events[-1].report.history == (failure,)
        assert failure.reason == "invalid_response"
        assert failure.identity == events[-1].identity
        assert failure.identity.wire_attempt == 1
        assert failure.identity.attempt_id is not None
        assert failure.identity.logical_request_id is not None
        assert failure.progress.raw_bytes == len(body)
        assert failure.progress.headers_received
        assert failure.progress.observed_content == content
        assert failure.progress.observed_reasoning == reasoning
        assert failure.progress.observed_tool_fragments == tools
        assert failure.progress.completed_tool_calls == completed
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
        assert [event.transition for event in lifecycle] == [
            "attempt_started",
            "attempt_failed",
            {False: "exhausted", True: "interrupted"}[failure.progress.semantic],
        ]
        sent = [event for event in captures if event.kind == "request"]
        assert [event.body for event in sent] == [requests[0][1]]
        assert (
            b"".join(event.body for event in captures if event.kind == "body") == body
        )
        assert all(event.identity == failure.identity for event in captures)
        safe = "".join(
            event.model_dump_json() + repr(event) for event in events + lifecycle
        )
        assert "eof-secret" not in safe
        assert "unfinished" not in safe

    async def should_recover_clean_keepalive_eof_after_admission(self, captures):
        lifecycle, admissions = [], []

        async def admit(context):
            admissions.append(context)
            return "allow"

        body = ndjson(done=False, message={})
        with scripted_http([(200, {}, body), (200, {}, frame("retried") + b"\n")]) as (
            host,
            requests,
        ):
            events = await collect(
                OllamaGateway(
                    host=host,
                    recovery_policy=RecoveryPolicy(
                        max_attempts=2,
                        base_delay=0,
                        admission=admit,
                        observer=lifecycle.append,
                        wire_observer=captures.append,
                    ),
                )
            )

        assert len(requests) == 2
        assert requests[0][1] == requests[1][1]
        assert events[-1].kind == "completed"
        assert events[-1].report.history[0].eligible
        assert events[-1].report.history[0].inspect_response() == body
        assert len(admissions) == 1
        assert admissions[0].previous_identity == events[-1].report.history[0].identity
        assert admissions[0].next_attempt == 2
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
        assert [
            event.identity.wire_attempt for event in captures if event.kind == "request"
        ] == [1, 2]
        assert (
            len(
                {
                    event.identity.attempt_id
                    for event in captures
                    if event.kind == "request"
                }
            )
            == 2
        )
        assert len({event.identity.logical_request_id for event in captures}) == 1
        assert [event.kind for event in events] == [
            "progress",
            "progress",
            "metrics",
            "content",
            "completed",
        ]
        assert events[-1].report.progress.delivered_content == len("retried")
        assert not events[-1].report.history[0].progress.semantic

    @pytest.mark.parametrize(
        "decision,outcome,count",
        [
            (None, "admission_required", 1),
            ("reject", "admission_rejected", 1),
            ("allow", "attempts_exhausted", 3),
        ],
    )
    @pytest.mark.parametrize("extra_bytes", [0, 10])
    async def should_require_admission_and_bound_keepalive_eof_history(
        self, decision, outcome, count, extra_bytes, captures
    ):
        admissions, lifecycle = [], []

        async def admit(context):
            admissions.append(context)
            return decision

        body = ndjson(done=False, message={})
        headers = {
            "Content-Length": str(len(body) + extra_bytes),
            "X-Evidence": "keepalive-secret",
        }
        with scripted_http([(200, headers, body)] * 3) as (host, requests):
            events = await collect(
                OllamaGateway(
                    host=host,
                    recovery_policy=RecoveryPolicy(
                        max_attempts=3,
                        base_delay=0,
                        admission={True: None, False: admit}[decision is None],
                        observer=lifecycle.append,
                        wire_observer=captures.append,
                    ),
                )
            )

        terminal = events[-1]
        assert len(requests) == count
        assert terminal.kind == "failed"
        assert terminal.outcome.value == outcome
        assert len(terminal.report.history) == count
        assert [
            failure.identity.wire_attempt for failure in terminal.report.history
        ] == list(range(1, count + 1))
        assert (
            len({failure.identity.attempt_id for failure in terminal.report.history})
            == count
        )
        assert all(
            failure.identity.attempt_id is not None
            for failure in terminal.report.history
        )
        assert (
            len(
                {
                    failure.identity.logical_request_id
                    for failure in terminal.report.history
                }
            )
            == 1
        )
        assert all(
            failure.category == "transport" and failure.eligible
            for failure in terminal.report.history
        )
        assert all(
            isinstance(failure.inspect_cause(), httpx.RemoteProtocolError)
            for failure in terminal.report.history
        )
        assert all(
            failure.inspect_response() == body for failure in terminal.report.history
        )
        assert all(
            dict(failure.inspect_headers())["x-evidence"] == "keepalive-secret"
            for failure in terminal.report.history
        )
        assert all(not failure.progress.semantic for failure in terminal.report.history)
        assert all(
            failure.progress.raw_bytes == len(body)
            for failure in terminal.report.history
        )
        assert [event.kind for event in events] == ["progress"] * count + ["failed"]
        assert [event.frame_index for event in events[:-1]] == [1] * count
        assert all(event.frame_progress.content_bytes == 0 for event in events[:-1])
        assert all(request[1] == requests[0][1] for request in requests)
        assert [event.body for event in captures if event.kind == "request"] == [
            request[1] for request in requests
        ]
        assert [
            context.failure.identity.wire_attempt for context in admissions
        ] == list(range(1, count)) + {None: [], "reject": [1], "allow": []}[decision]
        assert [event.transition for event in lifecycle] == {
            None: [
                "attempt_started",
                "attempt_failed",
                "admission_required",
                "exhausted",
            ],
            "reject": [
                "attempt_started",
                "attempt_failed",
                "admission_pending",
                "admission_rejected",
                "exhausted",
            ],
            "allow": [
                "attempt_started",
                "attempt_failed",
                "admission_pending",
                "admission_allowed",
                "delay_scheduled",
                "retry_started",
            ]
            * 2
            + ["attempt_started", "attempt_failed", "exhausted"],
        }[decision]


class DescribeStreamEOFCallers:
    @pytest.mark.parametrize("entrypoint", ["broker", "session"])
    @pytest.mark.parametrize(
        "decision,outcome,count",
        [
            (None, "admission_required", 1),
            ("reject", "admission_rejected", 1),
            ("allow", "succeeded", 2),
        ],
    )
    def should_propagate_clean_keepalive_eof_admission(
        self, entrypoint, decision, outcome, count, mocker, captures
    ):
        from mojentic.llm.chat_session import ChatSession
        from mojentic.llm.gateways.tokenizer_gateway import TokenizerGateway
        from mojentic.llm.llm_broker import LLMBroker

        async def admit(context):
            return decision

        tokenizer = mocker.Mock(spec=TokenizerGateway)
        tokenizer.encode.return_value = []
        body = ndjson(done=False, message={})
        with scripted_http([(200, {}, body), (200, {}, frame("answer") + b"\n")]) as (
            host,
            requests,
        ):
            gateway = OllamaGateway(
                host=host,
                recovery_policy=RecoveryPolicy(
                    max_attempts=2,
                    base_delay=0,
                    admission={True: None, False: admit}[decision is None],
                    wire_observer=captures.append,
                ),
            )
            broker = LLMBroker("test", gateway=gateway, tokenizer=tokenizer)
            session = ChatSession(broker, tokenizer_gateway=tokenizer)
            actions = {
                "broker": lambda: broker.generate_stream([LLMMessage(content="query")]),
                "session": lambda: session.send_stream("query"),
            }
            delivered, errors = [], []
            try:
                delivered.extend(actions[entrypoint]())
            except RecoveryError as error:
                errors.append(error)

        assert len(requests) == count
        assert delivered == {None: [], "reject": [], "allow": ["answer"]}[decision]
        assert [error.report.outcome for error in errors] == {
            None: [outcome],
            "reject": [outcome],
            "allow": [],
        }[decision]
        assert all(error.report.final_failure.eligible for error in errors)
        assert all(
            error.report.final_failure.inspect_response() == body for error in errors
        )
        assert all(request[1] == requests[0][1] for request in requests)
        assert (
            sum(message.role.value == "assistant" for message in session.messages)
            == {"broker": 0, "session": count - 1}[entrypoint]
        )

    @pytest.mark.parametrize("entrypoint", ["broker", "session"])
    @pytest.mark.parametrize("extra_bytes", [0, 10])
    @pytest.mark.parametrize(
        "body",
        [
            b'{"done":',
            frame("", tool_calls=[{"function": {"name": "counter", "arguments": {}}}]),
        ],
    )
    def should_propagate_unfinished_frames_without_tool_execution(
        self, entrypoint, extra_bytes, body, mocker, captures, counter_tool
    ):
        from mojentic.llm.chat_session import ChatSession
        from mojentic.llm.gateways.tokenizer_gateway import TokenizerGateway
        from mojentic.llm.llm_broker import LLMBroker

        tool = counter_tool
        tokenizer = mocker.Mock(spec=TokenizerGateway)
        tokenizer.encode.return_value = []
        with scripted_http(
            [
                (200, {"Content-Length": str(len(body) + extra_bytes)}, body),
                (200, {}, frame("retry") + b"\n"),
            ]
        ) as (host, requests):
            gateway = OllamaGateway(
                host=host,
                recovery_policy=RecoveryPolicy(
                    max_attempts=2,
                    base_delay=0,
                    admission=allow,
                    wire_observer=captures.append,
                ),
            )
            broker = LLMBroker("test", gateway=gateway, tokenizer=tokenizer)
            session = ChatSession(broker, tools=[tool], tokenizer_gateway=tokenizer)
            before = list(session.messages)
            actions = {
                "broker": lambda: broker.generate_stream(
                    [LLMMessage(content="query")], tools=[tool]
                ),
                "session": lambda: session.send_stream("query"),
            }
            delivered = []
            with pytest.raises(RecoveryError) as caught:
                delivered.extend(actions[entrypoint]())

        assert len(requests) == 1
        assert tool.calls == []
        assert delivered == []
        assert caught.value.report.final_failure.category == "protocol"
        assert caught.value.report.final_failure.inspect_response() == body
        assert len(caught.value.report.history) == 1
        assert session.messages[: len(before)] == before
        assert all(message.role.value != "assistant" for message in session.messages)


class DescribeSharedEOFClassificationSafety:
    @pytest.mark.parametrize("structured", [False, True])
    @pytest.mark.parametrize("status", [400, 401, 403])
    @pytest.mark.parametrize(
        "extra_bytes,cause_type",
        [(0, httpx.HTTPStatusError), (10, httpx.RemoteProtocolError)],
    )
    def should_preserve_permanent_status_for_ordinary_and_structured_requests(
        self, structured, status, extra_bytes, cause_type, captures
    ):
        from pydantic import BaseModel

        class Answer(BaseModel):
            answer: str

        body = b'{"error":"permanent-secret"}'
        with scripted_http(
            [(status, {"Content-Length": str(len(body) + extra_bytes)}, body)]
        ) as (host, requests):
            gateway = OllamaGateway(
                host=host,
                recovery_policy=RecoveryPolicy(
                    max_attempts=3,
                    base_delay=0,
                    admission=allow,
                    retryable_statuses=frozenset({status}),
                    wire_observer=captures.append,
                ),
            )
            with pytest.raises(RecoveryError) as caught:
                gateway.complete(
                    model="test",
                    messages=[LLMMessage(content="query")],
                    object_model={False: None, True: Answer}[structured],
                )

        failure = caught.value.report.final_failure
        assert len(requests) == 1
        assert failure.operation == {False: "ordinary", True: "structured"}[structured]
        assert failure.http_status == status
        assert failure.reason == "permanent"
        assert not failure.eligible
        assert failure.inspect_response() == body
        assert isinstance(failure.inspect_cause(), cause_type)
        assert len(caught.value.report.history) == 1
