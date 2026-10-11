"""Owned Ollama recovery streams with cancellation and explicit terminal events."""

import asyncio
import json
import threading
from collections.abc import AsyncIterator, Callable, Iterator
from enum import Enum
from typing import Literal
from uuid import uuid4

import httpx
from pydantic import BaseModel, ConfigDict, Field

from mojentic.llm.gateways.models import LLMGatewayResponse
from mojentic.llm.recovery import (
    Identity,
    Progress,
    RecoveryCall,
    RecoveryError,
    RecoveryPolicy,
    RecoveryReport,
    SafeModel,
    Timeout,
    WireEvent,
    _Attempt,
    _BudgetExpired,
    _guard,
    _HookError,
    _Recovery,
    parse_retry_after,
)

Decode = Callable[[dict], LLMGatewayResponse]


class StreamOutcome(str, Enum):
    """Terminal outcomes; exhaustion never denotes successful completion."""

    SUCCEEDED = "succeeded"
    INTERRUPTED = "interrupted"
    INELIGIBLE = "ineligible"
    ATTEMPTS_EXHAUSTED = "attempts_exhausted"
    ADMISSION_REQUIRED = "admission_required"
    ADMISSION_REJECTED = "admission_rejected"
    DELAY_CEILING = "delay_ceiling"
    BUDGET_EXHAUSTED = "budget_exhausted"
    CANCELLED = "cancelled"


class StreamFrameProgress(SafeModel):
    """Validated frame counters; content and reasoning lengths are UTF-8 bytes."""

    provider: Literal["ollama", "omlx"] = "ollama"
    done: bool
    content_bytes: int
    reasoning_bytes: int
    tool_call_count: int
    accumulated_tool_call_count: int


class StreamMetrics(SafeModel):
    """Reported provider counters and durations; missing values stay absent.

    Model and finish strings are sensitive provider evidence, excluded from default
    formatting and serialization. oMLX usage retains provider keys privately.
    Ollama throughput requires both reported inputs.
    """

    provider: Literal["ollama", "omlx"] = "ollama"
    provider_model: str | None = Field(default=None, exclude=True, repr=False)
    finish_reason: str | None = Field(default=None, exclude=True, repr=False)
    prompt_eval_count: int | None = None
    eval_count: int | None = None
    total_duration: int | None = None
    load_duration: int | None = None
    prompt_eval_duration: int | None = None
    eval_duration: int | None = None
    tokens_per_second: float | None = None
    usage: dict[str, object] | None = Field(default=None, exclude=True, repr=False)


class RecoveryStreamEvent(BaseModel):
    """Typed stream event. Semantic fields require explicit inspection to serialize.

    Progress and metrics carry validated provider evidence, never inferred counts.
    Failed events retain a privacy-safe exception with private cause inspection.
    """

    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)
    kind: Literal[
        "progress",
        "metrics",
        "content",
        "reasoning",
        "tool_fragment",
        "completed",
        "failed",
    ]
    identity: Identity
    progress: Progress
    frame_index: int = 0
    frame_progress: StreamFrameProgress | None = None
    metrics: StreamMetrics | None = None
    text: str | None = Field(default=None, exclude=True, repr=False)
    tools: tuple[dict, ...] = Field(default=(), exclude=True, repr=False)
    response: LLMGatewayResponse | None = Field(default=None, exclude=True, repr=False)
    report: RecoveryReport | None = None
    error: RecoveryError | None = Field(default=None, exclude=True, repr=False)
    outcome: StreamOutcome | None = None


class _Decoder:
    def __init__(self) -> None:
        self.index = 0
        self.content = ""
        self.thinking = ""
        self.tools = []
        self.evidence = {}
        self.terminal = False
        self.pending_observed = False
        self.observed_calls = 0
        self.observation_valid = True

    def observe(self, frame: object, attempt: _Attempt) -> None:
        message = frame.get("message", {}) if isinstance(frame, dict) else None
        if not isinstance(message, dict):
            self.observation_valid = False
            return
        calls = message.get("tool_calls")
        attempt.progress = attempt.progress.model_copy(
            update={
                "observed_content": attempt.progress.observed_content
                or bool(message.get("content")),
                "observed_reasoning": attempt.progress.observed_reasoning
                or bool(message.get("thinking")),
                "observed_tool_fragments": attempt.progress.observed_tool_fragments
                + (len(calls) if isinstance(calls, list) else 0),
            }
        )

        self.observe_completed_tools(frame, attempt)

    def observe_completed_tools(self, frame: object, attempt: _Attempt) -> None:
        try:
            _, calls = self.validate(frame)
        except (ValueError, TypeError):
            self.observation_valid = False
            return
        self.observed_calls += len(calls)
        if (
            self.observation_valid
            and frame.get("done") is True
            and frame.get("done_reason") == "stop"
        ):
            attempt.progress = attempt.progress.model_copy(
                update={"completed_tool_calls": self.observed_calls}
            )

    def validate(self, frame: object) -> tuple[dict, list[dict]]:
        if not isinstance(frame, dict) or self.terminal:
            raise ValueError("invalid stream frame")
        if frame.get("error") is not None:
            raise ValueError("provider error")
        message = frame.get("message", {})
        if not isinstance(message, dict):
            raise TypeError("invalid stream message")
        if message.get("role", "assistant") != "assistant":
            raise ValueError("invalid stream role")
        for key in ("content", "thinking"):
            if message.get(key) is not None and not isinstance(message[key], str):
                raise ValueError("invalid stream text")
        calls = message.get("tool_calls")
        calls = [] if calls is None else calls
        if not isinstance(calls, list):
            raise TypeError("invalid stream tools")
        for call in calls:
            self.validate_tool(call)
        self.validate_metadata(frame)
        return message, calls

    @staticmethod
    def validate_metadata(frame: dict) -> None:
        if "done" in frame and not isinstance(frame["done"], bool):
            raise ValueError("invalid done")
        if frame.get("done_reason") is not None and not isinstance(
            frame["done_reason"], str
        ):
            raise ValueError("invalid finish")
        for key in (
            "prompt_eval_count",
            "eval_count",
            "total_duration",
            "load_duration",
            "prompt_eval_duration",
            "eval_duration",
        ):
            if key in frame and (type(frame[key]) is not int or frame[key] < 0):
                raise ValueError("invalid metric")
        if frame.get("model") is not None and not isinstance(frame["model"], str):
            raise ValueError("invalid model")

    @staticmethod
    def validate_tool(call: object) -> None:
        if not isinstance(call, dict) or not isinstance(call.get("function"), dict):
            raise TypeError("invalid tool")
        if call.get("id") is not None and not isinstance(call["id"], str):
            raise TypeError("invalid tool id")
        function = call["function"]
        if not isinstance(function.get("name"), str) or not function["name"]:
            raise ValueError("invalid tool name")
        if not isinstance(function.get("arguments"), dict):
            raise TypeError("invalid tool arguments")

    def events(
        self, frame: object, attempt: _Attempt
    ) -> tuple[list[RecoveryStreamEvent], bool]:
        message, calls = self.validate(frame)
        self.index += 1
        content, thinking = message.get("content") or "", message.get("thinking") or ""
        done = frame.get("done", False)
        finish = frame.get("done_reason")
        common = {
            "identity": attempt.identity,
            "progress": attempt.progress,
            "frame_index": self.index,
        }
        output = [
            RecoveryStreamEvent(
                kind="progress",
                frame_progress=StreamFrameProgress(
                    done=done,
                    content_bytes=len(content.encode("utf-8")),
                    reasoning_bytes=len(thinking.encode("utf-8")),
                    tool_call_count=len(calls),
                    accumulated_tool_call_count=len(self.tools),
                ),
                **common,
            )
        ]
        for key in (
            "model",
            "prompt_eval_count",
            "eval_count",
            "total_duration",
            "load_duration",
            "prompt_eval_duration",
            "eval_duration",
        ):
            if key in frame:
                self.evidence[key] = frame[key]
        if done:
            self.evidence["done_reason"] = finish
            output.append(
                RecoveryStreamEvent(
                    kind="metrics",
                    metrics=self.metrics(frame),
                    **common,
                )
            )
        if done and finish != "stop":
            return output, False
        self.content += content
        self.thinking += thinking
        self.tools.extend(calls)
        if content:
            output.append(RecoveryStreamEvent(kind="content", text=content, **common))
        if thinking:
            output.append(
                RecoveryStreamEvent(kind="reasoning", text=thinking, **common)
            )
        for call in calls:
            output.append(
                RecoveryStreamEvent(kind="tool_fragment", tools=(call,), **common)
            )
        self.terminal = done
        return output, True

    @staticmethod
    def metrics(frame: dict) -> StreamMetrics:
        values = {
            key: frame[key]
            for key in (
                "prompt_eval_count",
                "eval_count",
                "total_duration",
                "load_duration",
                "prompt_eval_duration",
                "eval_duration",
            )
            if key in frame
        }
        throughput = None
        if frame.get("eval_count") is not None and frame.get("eval_duration"):
            throughput = frame["eval_count"] / (frame["eval_duration"] / 1_000_000_000)
        return StreamMetrics(
            provider_model=frame.get("model"),
            finish_reason=frame.get("done_reason"),
            tokens_per_second=throughput,
            **values,
        )


class _StreamRecovery(_Recovery):
    def __init__(
        self, policy: RecoveryPolicy, call: RecoveryCall, queue: asyncio.Queue
    ) -> None:
        super().__init__(policy, call, "streaming")
        self.queue = queue
        self.attempt = None
        self.terminal_failure = None
        self.exchange_cause: BaseException | None = None

    def decoder(self) -> _Decoder:
        return _Decoder()

    async def deliver(self, event: RecoveryStreamEvent, attempt: _Attempt) -> None:
        self.check_cancelled()
        acknowledged = asyncio.Event()
        await self.queue.put((event, acknowledged, attempt))
        await acknowledged.wait()
        self.check_cancelled()

    @staticmethod
    def build_request(
        client: httpx.AsyncClient, url: str, body: bytes, headers: dict
    ) -> httpx.Request:
        request = client.build_request("POST", url, content=body, headers=headers)
        if request.url.username or request.url.password:
            request = next(
                httpx.BasicAuth(request.url.username, request.url.password).auth_flow(
                    request
                )
            )
        return request

    async def exchange_stream(
        self,
        client: httpx.AsyncClient,
        url: str,
        body: bytes,
        headers: dict,
        attempt: _Attempt,
        decode: Decode,
    ) -> LLMGatewayResponse:
        self.check_dispatch()
        request = self.build_request(client, url, body, headers)
        self.capture(
            WireEvent(
                kind="request",
                identity=attempt.identity,
                body=body,
                headers=tuple(request.headers.multi_items()),
                url=str(request.url),
                method="POST",
            ),
            attempt,
        )
        self.check_dispatch()
        self.emit("attempt_started", attempt)
        self.check_dispatch()
        attempt.sent, attempt.phase = True, "awaiting_headers"
        response = await client.send(request, stream=True, auth=httpx.Auth())
        pending = b""
        try:
            attempt.status = response.status_code
            attempt.headers = tuple(response.headers.multi_items())
            attempt.retry_after = parse_retry_after(
                response.headers.get("retry-after"), self.policy.wall()
            )
            attempt.progress = Progress(headers_received=True)
            attempt.category = "protocol" if response.is_success else "http"
            attempt.phase = "streaming"
            self.capture(
                WireEvent(
                    kind="headers",
                    identity=attempt.identity,
                    status=attempt.status,
                    headers=attempt.headers,
                ),
                attempt,
            )
            decoder = self.decoder()
            async for chunk in response.aiter_raw():
                self.check_cancelled()
                attempt.raw += chunk
                attempt.progress = attempt.progress.model_copy(
                    update={"raw_bytes": len(attempt.raw)}
                )
                pending += chunk
                lines = pending.split(b"\n")
                pending = lines.pop()
                parsed, parse_error = [], None
                if response.is_success:
                    parsed, parse_error = self.observe_chunk(
                        lines, pending, decoder, attempt
                    )
                self.capture(
                    WireEvent(kind="body", identity=attempt.identity, body=chunk),
                    attempt,
                )
                self.check_cancelled()
                if parse_error is not None:
                    raise parse_error
                for frame in parsed:
                    await self.deliver_frame(frame, decoder, attempt)
                    if decoder.terminal:
                        return decode(self.response_frame(decoder))
            response.raise_for_status()
            if pending:
                attempt.category, attempt.reason = "protocol", "invalid_response"
                raise ValueError("stream ended with unfinished frame")
            raise httpx.RemoteProtocolError("stream ended without terminal proof")
        except httpx.TransportError:
            if response.is_success and pending:
                attempt.category, attempt.reason = "protocol", "invalid_response"
            raise
        finally:
            await response.aclose()

    def observe_chunk(
        self, lines: list[bytes], pending: bytes, decoder: _Decoder, attempt: _Attempt
    ) -> tuple[list[object], Exception | None]:
        parsed, parse_error = self.parse_lines(lines, decoder, attempt)
        if pending.strip() and not decoder.pending_observed:
            try:
                partial = json.loads(pending)
            except (ValueError, UnicodeDecodeError):
                pass
            else:
                decoder.observe(partial, attempt)
                decoder.pending_observed = True
        return parsed, parse_error

    @staticmethod
    def response_frame(decoder: _Decoder) -> dict:
        return decoder.evidence | {
            "done": True,
            "message": {
                "role": "assistant",
                "content": decoder.content,
                "thinking": decoder.thinking,
                "tool_calls": decoder.tools,
            },
        }

    @staticmethod
    def parse_lines(
        lines: list[bytes], decoder: _Decoder, attempt: _Attempt
    ) -> tuple[list[object], Exception | None]:
        frames, parse_error = [], None
        for index, line in enumerate(lines):
            already_observed = index == 0 and decoder.pending_observed
            if index == 0:
                decoder.pending_observed = False
            if not line.strip() or line.lstrip().startswith(b":"):
                continue
            try:
                frame = json.loads(line)
            except (ValueError, UnicodeDecodeError) as cause:
                parse_error = cause
                decoder.observation_valid = False
                continue
            if not already_observed:
                decoder.observe(frame, attempt)
            frames.append(frame)
        return frames, parse_error

    async def deliver_frame(
        self, frame: object, decoder: _Decoder, attempt: _Attempt
    ) -> None:
        if isinstance(frame, dict) and frame.get("error") is not None:
            attempt.category, attempt.reason = "provider_response", "provider_error"
        events, accepted = decoder.events(frame, attempt)
        if not accepted:
            attempt.category, attempt.reason = "protocol", "invalid_response"
            cause = ValueError("incomplete stream finish")
            self.terminal_failure = self.record_failure(attempt, cause)
        for event in events:
            await self.deliver(event, attempt)
        if not accepted:
            raise attempt.cause
        if decoder.terminal:
            attempt.progress = attempt.progress.model_copy(
                update={"completed_tool_calls": len(decoder.tools)}
            )

    async def observed_exchange(
        self,
        client: httpx.AsyncClient,
        url: str,
        body: bytes,
        headers: dict,
        attempt: _Attempt,
        decode: Decode,
    ) -> LLMGatewayResponse:
        try:
            return await self.exchange_stream(
                client, url, body, headers, attempt, decode
            )
        except (httpx.HTTPError, ValueError, TypeError, KeyError, _HookError) as cause:
            self.exchange_cause = cause
            raise

    async def run_stream(
        self, url: str, body: bytes, headers: dict, timeout: Timeout, decode: Decode
    ) -> None:
        async with httpx.AsyncClient(
            timeout=timeout,
            follow_redirects=False,
            trust_env=False,
            transport=httpx.AsyncHTTPTransport(retries=0),
        ) as client:
            for number in range(1, self.policy.max_attempts + 1):
                attempt = _Attempt(
                    identity=Identity(
                        logical_request_id=self.logical,
                        attempt_id=str(uuid4()),
                        wire_attempt=number,
                    ),
                    operation="streaming",
                    provider=self.provider,
                )
                self.attempt = attempt
                self.terminal_failure = None
                self.exchange_cause = None
                try:
                    result = await _guard(
                        self.observed_exchange(
                            client, url, body, headers, attempt, decode
                        ),
                        self.call,
                    )
                    self.check_cancelled()
                    report = RecoveryReport(
                        identity=attempt.identity,
                        history=tuple(self.history),
                        progress=attempt.progress,
                        outcome="succeeded",
                    )
                    await _guard(
                        self.deliver(
                            RecoveryStreamEvent(
                                kind="completed",
                                identity=attempt.identity,
                                progress=attempt.progress,
                                response=result,
                                report=report,
                                outcome=StreamOutcome.SUCCEEDED,
                            ),
                            attempt,
                        ),
                        self.call,
                    )
                    self.emit("attempt_succeeded", attempt)
                    self.check_cancelled()
                    return
                except asyncio.CancelledError as cause:
                    if (
                        self.terminal_failure is None
                        and self.exchange_cause is not None
                    ):
                        self.terminal_failure = self.record_failure(
                            attempt, self.exchange_cause
                        )
                    if self.terminal_failure is not None:
                        try:
                            self.emit("attempt_failed", attempt, self.terminal_failure)
                        except _HookError as observer_error:
                            self.callback_failure(attempt, observer_error)
                    self.cancel(
                        attempt, cause, recorded=self.terminal_failure is not None
                    )
                except _BudgetExpired as cause:
                    attempt.category, attempt.reason = (
                        "client_timeout",
                        "budget_exhausted",
                    )
                    failure = self.record_failure(attempt, cause)
                    outcome = "budget_exhausted"
                    try:
                        self.emit("exhausted", attempt, failure)
                    except _HookError as observer_error:
                        failure = self.callback_failure(attempt, observer_error)
                        outcome = "interrupted"
                    raise self.error(outcome, attempt, failure) from None
                except (
                    httpx.HTTPError,
                    ValueError,
                    TypeError,
                    KeyError,
                    _HookError,
                ) as cause:
                    failure = self.terminal_failure or self.record_failure(
                        attempt, cause
                    )
                    await self.failed(attempt, failure)

    async def produce(
        self, url: str, body: bytes, headers: dict, timeout: Timeout, decode: Decode
    ) -> None:
        try:
            await self.run_stream(url, body, headers, timeout, decode)
        except RecoveryError as error:
            await self.queue.put(
                (
                    RecoveryStreamEvent(
                        kind="failed",
                        identity=error.report.identity,
                        progress=error.report.progress,
                        report=error.report,
                        error=error,
                        outcome=StreamOutcome(error.report.outcome),
                    ),
                    None,
                    self.attempt,
                )
            )


async def recover_stream(
    url: str,
    body: bytes,
    headers: dict,
    timeout: Timeout,
    decode: Decode,
    policy: RecoveryPolicy,
    call: RecoveryCall,
    *,
    _engine_type: type[_StreamRecovery] = _StreamRecovery,
) -> AsyncIterator[RecoveryStreamEvent]:
    """Own HTTP and admission tasks even while a consumer is paused.

    Closing the iterator cancels local resources; remote termination stays unknown.
    """
    queue = asyncio.Queue()
    engine = _engine_type(policy, call, queue)

    producer = asyncio.create_task(engine.produce(url, body, headers, timeout, decode))
    acknowledged = None
    try:
        while True:
            if acknowledged is not None:
                acknowledged.set()
            event, acknowledged, attempt = await _next_event(queue, producer)
            if call.cancelled and event.kind != "failed":
                continue
            if event.kind == "completed":
                acknowledged.set()
                await producer
                if not queue.empty():
                    event, acknowledged, attempt = queue.get_nowait()
                elif call.cancelled:
                    continue
            event = _delivered(event, attempt)
            yield event
            if event.kind in {"completed", "failed"}:
                if acknowledged is not None:
                    acknowledged.set()
                await producer
                return
    finally:
        if not producer.done():
            producer.cancel()
        await asyncio.gather(producer, return_exceptions=True)


async def _next_event(queue: asyncio.Queue, producer: asyncio.Task) -> tuple:
    received = asyncio.create_task(queue.get())
    try:
        done, _ = await asyncio.wait(
            {received, producer}, return_when=asyncio.FIRST_COMPLETED
        )
        if received in done:
            return received.result()
        await producer
        return await received
    finally:
        if not received.done():
            received.cancel()
        await asyncio.gather(received, return_exceptions=True)


def _delivered(event: RecoveryStreamEvent, attempt: _Attempt) -> RecoveryStreamEvent:
    field = {
        "content": "delivered_content",
        "reasoning": "delivered_reasoning",
        "tool_fragment": "delivered_tool_fragments",
    }.get(event.kind)
    if field:
        count = len(event.text.encode("utf-8")) if event.text else len(event.tools)
        attempt.progress = attempt.progress.model_copy(
            update={field: getattr(attempt.progress, field) + count}
        )
    if event.kind == "completed":
        attempt.progress = attempt.progress.model_copy(
            update={"delivered_tool_calls": len(event.response.tool_calls)}
        )
    event = event.model_copy(update={"progress": attempt.progress})
    if event.report is not None:
        report = event.report.model_copy(update={"progress": attempt.progress})
        event = event.model_copy(update={"report": report})
        if event.response is not None:
            event.response.recovery_report = report
    return event


def synchronous_stream(
    stream: AsyncIterator[RecoveryStreamEvent],
) -> Iterator[RecoveryStreamEvent]:
    """Bridge synchronous broker callers to an independently running owned loop."""
    loop = asyncio.new_event_loop()
    thread = threading.Thread(target=loop.run_forever, daemon=True)
    thread.start()
    try:
        while True:
            future = asyncio.run_coroutine_threadsafe(anext(stream), loop)
            try:
                yield future.result()
            except StopAsyncIteration:
                return
    finally:
        asyncio.run_coroutine_threadsafe(stream.aclose(), loop).result()
        loop.call_soon_threadsafe(loop.stop)
        thread.join()
        loop.close()
