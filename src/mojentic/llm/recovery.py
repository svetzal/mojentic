"""Opt-in request recovery. Admission authorizes a resend, never inference termination.

Safe models exclude wire payloads and original exceptions. Inspect these explicitly
on ``RecoveryError`` or capture them with the caller-owned wire observer.
"""

import asyncio
import inspect
import json
import math
import secrets
import threading
import time
from collections.abc import Awaitable, Callable
from datetime import UTC
from email.utils import parsedate_to_datetime
from typing import Literal, TypeVar
from uuid import uuid4

import httpx
from pydantic import BaseModel, ConfigDict, Field, PrivateAttr

Result = TypeVar("Result")
Timeout = httpx.Timeout | float | None


class SafeModel(BaseModel):
    """Immutable, payload-free public evidence."""

    model_config = ConfigDict(frozen=True, extra="forbid")


class Identity(SafeModel):
    """One logical completion and one actual HTTP request."""

    logical_request_id: str
    attempt_id: str | None
    wire_attempt: int


class Progress(SafeModel):
    """Observed semantics are distinct from delivered ordinary completion output."""

    headers_received: bool = False
    raw_bytes: int = 0
    observed_content: bool = False
    observed_reasoning: bool = False
    observed_tool_fragments: int = 0
    completed_tool_calls: int = 0
    delivered_content: int = 0
    delivered_reasoning: int = 0
    delivered_tool_fragments: int = 0
    delivered_tool_calls: int = 0

    @property
    def semantic(self) -> bool:
        """Whether any semantic output was observed or delivered."""
        return any(
            (
                self.observed_content,
                self.observed_reasoning,
                self.observed_tool_fragments,
                self.completed_tool_calls,
                self.delivered_content,
                self.delivered_reasoning,
                self.delivered_tool_fragments,
                self.delivered_tool_calls,
            )
        )


class RetryAfter(SafeModel):
    """A parsed minimum delay; raw untrusted header text is never retained here."""

    state: Literal["absent", "invalid", "seconds", "date"] = "absent"
    delay: float | None = None


def parse_retry_after(value: str | None, wall: float) -> RetryAfter:
    """Parse seconds or an HTTP date against the observed wall clock."""
    if value is None:
        return RetryAfter()
    if value.isascii() and value.isdigit():
        try:
            delay = float(value)
            if math.isfinite(delay):
                return RetryAfter(state="seconds", delay=delay)
        except ValueError:
            pass
        return RetryAfter(state="invalid")
    try:
        date = parsedate_to_datetime(value)
        if date.tzinfo is None:
            date = date.replace(tzinfo=UTC)
        return RetryAfter(state="date", delay=max(0, date.timestamp() - wall))
    except (ValueError, TypeError, OverflowError):
        pass
    return RetryAfter(state="invalid")


class Failure(SafeModel):
    """Stable classification and evidence for a completed failed wire attempt."""

    provider: Literal["ollama"] = "ollama"
    operation: Literal["ordinary", "structured", "streaming"]
    category: Literal[
        "transport",
        "http",
        "provider_response",
        "protocol",
        "cancellation",
        "client_timeout",
    ]
    identity: Identity
    http_status: int | None = None
    provider_code: str | None = None
    provider_request_id: str | None = None
    retry_after: RetryAfter = Field(default_factory=RetryAfter)
    phase: (
        Literal["connecting", "sending", "awaiting_headers", "streaming", "decoding"]
        | None
    ) = None
    acceptance: Literal["yes", "no", "unknown"] = "unknown"
    progress: Progress = Field(default_factory=Progress)
    eligible: bool = False
    reason: str
    _original_cause: BaseException | None = PrivateAttr(default=None)
    _response_bytes: bytes = PrivateAttr(default=b"")
    _response_headers: tuple[tuple[str, str], ...] = PrivateAttr(default=())

    def inspect_cause(self) -> BaseException | None:
        """Inspect the original exception, whose text may contain secrets."""
        return self._original_cause

    def inspect_response(self) -> bytes:
        """Inspect exact response evidence for this failure."""
        return self._response_bytes

    def inspect_headers(self) -> tuple[tuple[str, str], ...]:
        """Inspect private response headers, including untrusted metadata."""
        return self._response_headers


class RecoveryReport(SafeModel):
    """Bounded wire history, including the final attempt on success or failure."""

    identity: Identity
    history: tuple[Failure, ...] = ()
    progress: Progress
    outcome: str
    final_failure: Failure | None = None


class RecoveryError(Exception):
    """Privacy-safe exception with explicitly inspectable original evidence.

    Parameters
    ----------
    report : RecoveryReport
        Safe wire accounting and final failure.
    causes : tuple[BaseException, ...]
        Private original exceptions, in failure order.
    responses : tuple[bytes, ...]
        Private response evidence, in failure order.
    """

    def __init__(
        self,
        report: RecoveryReport,
        causes: tuple[BaseException, ...],
        responses: tuple[bytes, ...],
    ):
        self.report = report
        self._causes = causes
        self._responses = responses
        super().__init__(
            f"ollama recovery {report.outcome}; wire attempts={report.identity.wire_attempt}"
        )

    def inspect_cause(self, index: int = -1) -> BaseException:
        """Return the original cause; its formatting may contain sensitive data."""
        return self._causes[index]

    def inspect_response(self, index: int = -1) -> bytes:
        """Return exact private response bytes for a failed attempt."""
        return self._responses[index]

    def inspect_headers(self, index: int = -1) -> tuple[tuple[str, str], ...]:
        """Inspect response headers of the final failure or a history entry."""
        failure = (
            self.report.final_failure if index == -1 else self.report.history[index]
        )
        return failure.inspect_headers() if failure is not None else ()


class LifecycleEvent(SafeModel):
    """Payload-free transition, emitted in request order."""

    transition: str
    identity: Identity
    progress: Progress
    failure: Failure | None = None
    delay: float | None = None


class AdmissionContext(SafeModel):
    """Explicit permission request; a pending coroutine gives no permission."""

    failure: Failure
    next_attempt: int
    previous_identity: Identity


class WireEvent(BaseModel):
    """Sensitive caller-owned capture event; never included in lifecycle models."""

    model_config = ConfigDict(frozen=True)
    kind: Literal["request", "headers", "body"]
    identity: Identity
    body: bytes = Field(default=b"", repr=False)
    headers: tuple[tuple[str, str], ...] = Field(default=(), repr=False)
    status: int | None = None
    url: str | None = Field(default=None, repr=False)
    method: str | None = None


class RecoveryCall:
    """Thread-safe cancellation for one call; closing HTTP does not prove termination."""

    def __init__(self) -> None:
        self._cancelled = threading.Event()

    def cancel(self) -> None:
        """Cancel active HTTP, admission, or backoff."""
        self._cancelled.set()

    @property
    def cancelled(self) -> bool:
        """Whether the caller requested cancellation."""
        return self._cancelled.is_set()

    async def wait(self) -> None:
        """Wait without blocking the event loop or leaving a worker thread behind."""
        while not self.cancelled:
            await asyncio.sleep(0.005)


def _jitter(ceiling: float) -> float:
    return ceiling * secrets.randbelow(2**53) / 2**53


class RecoveryPolicy(BaseModel):
    """Opt-in bounded recovery with injectable timing and caller admission.

    ``deadline`` is absolute monotonic time. ``budget`` starts at the first
    failure. Neither imposes a timeout on an admitted active generation.
    Callbacks and timing functions are private to policy serialization.
    """

    model_config = ConfigDict(
        frozen=True, arbitrary_types_allowed=True, extra="forbid", allow_inf_nan=False
    )
    max_attempts: int = Field(default=1, ge=1, strict=True)
    base_delay: float = Field(default=0.1, ge=0)
    delay_ceiling: float = Field(default=30, ge=0)
    retryable_statuses: frozenset[int] = frozenset({429, 500, 502, 503, 504})
    retryable_categories: frozenset[str] = frozenset(
        {"transport", "http", "client_timeout"}
    )
    budget: float | None = Field(default=None, ge=0)
    deadline: float | None = None
    admission: (
        Callable[[AdmissionContext], Awaitable[Literal["allow", "reject"]]] | None
    ) = Field(default=None, exclude=True, repr=False)
    observer: Callable[[LifecycleEvent], None] | None = Field(
        default=None, exclude=True, repr=False
    )
    wire_observer: Callable[[WireEvent], None] | None = Field(
        default=None, exclude=True, repr=False
    )
    monotonic: Callable[[], float] = Field(
        default=time.monotonic, exclude=True, repr=False
    )
    wall: Callable[[], float] = Field(default=time.time, exclude=True, repr=False)
    jitter: Callable[[float], float] = Field(default=_jitter, exclude=True, repr=False)
    sleeper: Callable[[float], Awaitable[None]] = Field(
        default=asyncio.sleep, exclude=True, repr=False
    )

    def delay(self, failure: Failure) -> float | None:
        """Bounded full jitter with Retry-After as a minimum, never shortened."""
        exponent = min(failure.identity.wire_attempt - 1, 1023)
        ceiling = min(self.delay_ceiling, self.base_delay * 2.0**exponent)
        jittered = _invoke(self.jitter, ceiling)
        if not math.isfinite(jittered) or not 0 <= jittered <= ceiling:
            raise ValueError("invalid jitter result")
        minimum = failure.retry_after.delay or 0
        return max(minimum, jittered) if minimum <= self.delay_ceiling else None


class Capabilities(SafeModel):
    """Only facilities implemented and evidenced by this adapter."""

    ordinary_recovery: bool = True
    structured_recovery: bool = True
    streaming_recovery: bool = False
    remote_cancellation: Literal["unsupported"] = "unsupported"
    request_status: Literal["unsupported"] = "unsupported"
    inference_termination: Literal["unknown"] = "unknown"
    idempotency: Literal["unsupported"] = "unsupported"
    exact_wire_capture: bool = True


class _Attempt(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    identity: Identity
    operation: Literal["ordinary", "structured", "streaming"]
    progress: Progress = Field(default_factory=Progress)
    status: int | None = None
    request_id: str | None = None
    retry_after: RetryAfter = Field(default_factory=RetryAfter)
    raw: bytes = Field(default=b"", repr=False)
    headers: tuple[tuple[str, str], ...] = Field(default=(), repr=False)
    phase: str | None = None
    category: str = "transport"
    reason: str = "transient"
    cause: BaseException | None = Field(default=None, repr=False)
    sent: bool = False

    def blocked_reason(self) -> str | None:
        if self.category == "cancellation":
            return "cancelled"
        if self.status in {400, 401, 403}:
            return "permanent"
        if self.operation != "streaming" and self.progress.semantic:
            return "semantic_output"
        if self.reason in {
            "capture_failed",
            "observer_failed",
            "admission_failed",
            "policy_failed",
            "invalid_response",
            "provider_error",
            "budget_exhausted",
        }:
            return self.reason
        if self.progress.semantic:
            return "semantic_output"
        if (
            self.operation != "streaming"
            and self.status is not None
            and 200 <= self.status < 300
            and self.raw
        ):
            return "uncertain_response"
        return None

    def failure(self, policy: RecoveryPolicy) -> Failure:
        blocked = self.blocked_reason()
        eligible = False
        if blocked is None and self.category in policy.retryable_categories:
            eligible = self.category in {"transport", "client_timeout"} or (
                self.category == "http" and self.status in policy.retryable_statuses
            )
        reason = blocked or ("transient" if eligible else "permanent")
        failure = Failure(
            operation=self.operation,
            category=self.category,
            identity=self.identity,
            http_status=self.status,
            provider_request_id=self.request_id,
            retry_after=self.retry_after,
            phase=self.phase,
            progress=self.progress,
            acceptance="unknown" if self.sent else "no",
            eligible=eligible,
            reason=reason,
        )
        failure._original_cause = self.cause
        failure._response_bytes = self.raw
        failure._response_headers = self.headers
        return failure

    def observe_semantics(self) -> None:
        try:
            frame = json.loads(self.raw)
        except (ValueError, UnicodeDecodeError):
            return
        if not isinstance(frame, dict) or not isinstance(frame.get("message"), dict):
            return
        message = frame["message"]
        calls = message.get("tool_calls")
        count = len(calls) if isinstance(calls, list) else 0
        self.progress = self.progress.model_copy(
            update={
                "observed_content": bool(message.get("content")),
                "observed_reasoning": bool(message.get("thinking")),
                "observed_tool_fragments": count,
                "completed_tool_calls": count if frame.get("done") is True else 0,
            }
        )


class _HookError(Exception):
    def __init__(self, original: Exception) -> None:
        self.original = original
        super().__init__("caller callback failed")


def _invoke(callback: Callable[..., Result], *args: object) -> Result:
    try:
        return callback(*args)
    except Exception as cause:
        raise _HookError(cause) from cause


async def _sleep(sleeper: Callable[[float], Awaitable[None]], delay: float) -> None:
    try:
        await sleeper(delay)
    except Exception as cause:
        raise _HookError(cause) from cause


class _BudgetExpired(Exception):
    pass


def _require_synchronous(value: object) -> None:
    if inspect.isawaitable(value):
        if inspect.iscoroutine(value):
            value.close()
        raise TypeError("observers must be synchronous")


async def _guard(
    awaitable: Awaitable[Result], call: RecoveryCall, remaining: float | None = None
) -> Result:
    if call.cancelled:
        if hasattr(awaitable, "close"):
            awaitable.close()
        raise asyncio.CancelledError()
    task = asyncio.ensure_future(awaitable)
    cancel = asyncio.create_task(call.wait())
    try:
        done, _ = await asyncio.wait(
            {task, cancel}, timeout=remaining, return_when=asyncio.FIRST_COMPLETED
        )
        if call.cancelled or cancel in done:
            raise asyncio.CancelledError()
        if task not in done:
            raise _BudgetExpired()
        result = task.result()
        if call.cancelled:
            raise asyncio.CancelledError()
        return result
    finally:
        for pending in (task, cancel):
            if not pending.done():
                pending.cancel()
        await asyncio.gather(task, cancel, return_exceptions=True)


class _Recovery:
    def __init__(
        self,
        policy: RecoveryPolicy,
        call: RecoveryCall,
        operation: Literal["ordinary", "structured", "streaming"],
    ) -> None:
        self.policy = policy
        self.call = call
        self.operation = operation
        self.logical = str(uuid4())
        self.history: list[Failure] = []
        self.causes: list[BaseException] = []
        self.responses: list[bytes] = []
        self.first_failure: float | None = None
        self.observer_failed = False

    def emit(
        self,
        transition: str,
        attempt: _Attempt,
        failure: Failure | None = None,
        delay: float | None = None,
    ) -> None:
        if self.policy.observer and not self.observer_failed:
            try:
                observed = self.policy.observer(
                    LifecycleEvent(
                        transition=transition,
                        identity=attempt.identity,
                        progress=attempt.progress,
                        failure=failure,
                        delay=delay,
                    )
                )
                _require_synchronous(observed)
            except Exception as cause:
                self.observer_failed = True
                attempt.category, attempt.reason = "protocol", "observer_failed"
                raise _HookError(cause) from cause

    def capture(self, event: WireEvent, attempt: _Attempt) -> None:
        if self.policy.wire_observer:
            try:
                observed = self.policy.wire_observer(event)
                _require_synchronous(observed)
            except Exception as cause:
                attempt.category, attempt.reason = "protocol", "capture_failed"
                raise _HookError(cause) from cause

    def remaining(self) -> float | None:
        limits = []
        if self.policy.deadline is not None:
            limits.append(self.policy.deadline - self.policy.monotonic())
        if self.policy.budget is not None and self.first_failure is not None:
            limits.append(
                self.first_failure + self.policy.budget - self.policy.monotonic()
            )
        return max(0, min(limits)) if limits else None

    def error(self, outcome: str, attempt: _Attempt, failure: Failure) -> RecoveryError:
        return RecoveryError(
            RecoveryReport(
                identity=attempt.identity,
                history=tuple(self.history),
                progress=attempt.progress,
                outcome=outcome,
                final_failure=failure,
            ),
            tuple(self.causes),
            tuple(self.responses),
        )

    async def exchange(
        self,
        client: httpx.AsyncClient,
        url: str,
        body: bytes,
        headers: dict,
        attempt: _Attempt,
        decode: Callable[[object], Result],
    ) -> Result:
        self.check_dispatch()
        request = client.build_request("POST", url, content=body, headers=headers)
        # Resolve URL Basic authentication before capture; disable implicit auth
        # on send so HTTPX cannot mutate the captured request afterwards.
        if request.url.username or request.url.password:
            request = next(
                httpx.BasicAuth(request.url.username, request.url.password).auth_flow(
                    request
                )
            )
        self.capture(
            WireEvent(
                kind="request",
                identity=attempt.identity,
                body=body,
                url=str(request.url),
                method="POST",
                headers=tuple(request.headers.multi_items()),
            ),
            attempt,
        )
        self.check_dispatch()
        self.emit("attempt_started", attempt)
        self.check_dispatch()
        attempt.sent = True
        attempt.phase = "awaiting_headers"
        response = await client.send(request, stream=True, auth=httpx.Auth())
        try:
            attempt.status = response.status_code
            # Even syntactically valid UUIDs can echo outbound secrets. Keep
            # provider metadata exclusively in explicit private inspection.
            attempt.headers = tuple(response.headers.multi_items())
            attempt.retry_after = parse_retry_after(
                response.headers.get("retry-after"), self.policy.wall()
            )
            attempt.progress = Progress(headers_received=True)
            attempt.category = "http" if not response.is_success else "protocol"
            attempt.phase = "decoding"
            self.capture(
                WireEvent(
                    kind="headers",
                    identity=attempt.identity,
                    status=response.status_code,
                    headers=tuple(response.headers.multi_items()),
                ),
                attempt,
            )
            self.check_cancelled()
            async for chunk in response.aiter_raw():
                attempt.raw += chunk
                attempt.progress = attempt.progress.model_copy(
                    update={"raw_bytes": len(attempt.raw)}
                )
                # Update observed semantics before the capture hook can fail.
                attempt.observe_semantics()
                self.capture(
                    WireEvent(kind="body", identity=attempt.identity, body=chunk),
                    attempt,
                )
                self.check_cancelled()
            response.raise_for_status()
            try:
                frame = json.loads(attempt.raw)
                if isinstance(frame, dict) and "error" in frame:
                    attempt.category, attempt.reason = (
                        "provider_response",
                        "provider_error",
                    )
                    raise ValueError("provider error response")
                result = decode(frame)
            except (ValueError, TypeError, KeyError):
                if attempt.reason != "provider_error":
                    attempt.category, attempt.reason = "protocol", "invalid_response"
                raise
            return result
        finally:
            await response.aclose()

    def check_cancelled(self) -> None:
        if self.call.cancelled:
            raise asyncio.CancelledError()

    def check_dispatch(self) -> None:
        self.check_cancelled()
        remaining = self.remaining()
        if remaining is not None and remaining <= 0:
            raise _BudgetExpired()

    async def admit(self, attempt: _Attempt, failure: Failure) -> str | None:
        if self.policy.admission is None:
            self.emit("admission_required", attempt, failure)
            return "admission_required"
        self.emit("admission_pending", attempt, failure)
        try:
            decision = await _guard(
                self.policy.admission(
                    AdmissionContext(
                        failure=failure,
                        next_attempt=attempt.identity.wire_attempt + 1,
                        previous_identity=attempt.identity,
                    )
                ),
                self.call,
                self.remaining(),
            )
        except _BudgetExpired:
            raise
        except Exception as cause:
            attempt.category, attempt.reason = "protocol", "admission_failed"
            raise _HookError(cause) from cause
        if decision != "allow":
            self.emit("admission_rejected", attempt, failure)
            return "admission_rejected"
        self.emit("admission_allowed", attempt, failure)
        return None

    def record_failure(self, attempt: _Attempt, cause: BaseException) -> Failure:
        cause = cause.original if isinstance(cause, _HookError) else cause
        attempt.cause = cause
        if attempt.reason == "invalid_response":
            attempt.category = "protocol"
        elif isinstance(cause, httpx.TimeoutException):
            attempt.category = "client_timeout"
        elif isinstance(cause, httpx.TransportError):
            attempt.category = "transport"
        elif isinstance(cause, httpx.HTTPStatusError):
            attempt.category = "http"
        elif attempt.reason == "transient":
            attempt.category, attempt.reason = "protocol", "invalid_response"
        if not attempt.sent:
            attempt.identity = attempt.identity.model_copy(
                update={
                    "wire_attempt": attempt.identity.wire_attempt - 1,
                    "attempt_id": None,
                }
            )
        failure = attempt.failure(self.policy)
        if attempt.sent:
            self.history.append(failure)
        self.causes.append(cause)
        self.responses.append(attempt.raw)
        if self.first_failure is None:
            self.first_failure = self.policy.monotonic()
        return failure

    def callback_failure(self, attempt: _Attempt, cause: BaseException) -> Failure:
        cause = cause.original if isinstance(cause, _HookError) else cause
        attempt.category, attempt.cause = "protocol", cause
        if attempt.reason == "transient":
            attempt.reason = "policy_failed"
        self.causes.append(cause)
        self.responses.append(attempt.raw)
        return attempt.failure(self.policy)

    async def failed(self, attempt: _Attempt, failure: Failure) -> None:
        try:
            self.emit("attempt_failed", attempt, failure)
            outcome = await self.retry(attempt, failure)
            if outcome is None:
                return
        except asyncio.CancelledError as cause:
            self.cancel(attempt, cause, recorded=True)
        except _BudgetExpired:
            outcome = "budget_exhausted"
        except (ValueError, TypeError, _HookError) as cause:
            failure = self.callback_failure(attempt, cause)
            outcome = "interrupted"
        try:
            self.emit(
                "interrupted" if outcome == "interrupted" else "exhausted",
                attempt,
                failure,
            )
        except _HookError as cause:
            failure = self.callback_failure(attempt, cause)
            outcome = "interrupted"
            self.emit("interrupted", attempt, failure)
        raise self.error(outcome, attempt, failure) from None

    async def run(
        self,
        url: str,
        body: bytes,
        headers: dict,
        timeout: Timeout,
        decode: Callable[[object], Result],
    ) -> tuple[Result, RecoveryReport]:
        # No SDK retry layer, redirects, proxy discovery, or fixed generation timeout.
        async with httpx.AsyncClient(
            timeout=timeout,
            follow_redirects=False,
            trust_env=False,
            transport=httpx.AsyncHTTPTransport(retries=0),
        ) as client:
            for number in range(1, self.policy.max_attempts + 1):
                identity = Identity(
                    logical_request_id=self.logical,
                    attempt_id=str(uuid4()),
                    wire_attempt=number,
                )
                attempt = _Attempt(identity=identity, operation=self.operation)
                try:
                    result = await _guard(
                        self.exchange(client, url, body, headers, attempt, decode),
                        self.call,
                    )
                    self.check_cancelled()
                    self.emit("attempt_succeeded", attempt)
                    self.check_cancelled()
                except asyncio.CancelledError as cause:
                    self.cancel(attempt, cause)
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
                    failure = self.record_failure(attempt, cause)
                    await self.failed(attempt, failure)
                    continue
                attempt.progress = attempt.progress.model_copy(
                    update={
                        "delivered_content": len(result.content or ""),
                        "delivered_reasoning": len(result.thinking or ""),
                        "delivered_tool_calls": len(result.tool_calls),
                    }
                )
                report = RecoveryReport(
                    identity=attempt.identity,
                    history=tuple(self.history),
                    progress=attempt.progress,
                    outcome="succeeded",
                )
                return result, report
        raise RuntimeError("unreachable recovery state")

    def limit_refusal(self, delay: float | None) -> str | None:
        if delay is None:
            return "delay_ceiling"
        remaining = self.remaining()
        if remaining is not None and (remaining <= 0 or delay > remaining):
            return "budget_exhausted"
        return None

    async def retry(self, attempt: _Attempt, failure: Failure) -> str | None:
        if self.call.cancelled:
            raise asyncio.CancelledError()
        if not failure.eligible:
            return (
                "interrupted"
                if failure.progress.semantic or failure.reason == "capture_failed"
                else "ineligible"
            )
        if attempt.identity.wire_attempt >= self.policy.max_attempts:
            return "attempts_exhausted"
        refusal = self.limit_refusal(0)
        if refusal:
            return refusal
        delay = self.policy.delay(failure)
        refusal = self.limit_refusal(delay)
        if refusal:
            return refusal
        outcome = await self.admit(attempt, failure)
        if outcome:
            return outcome
        refusal = self.limit_refusal(delay)
        if refusal:
            return refusal
        self.emit("delay_scheduled", attempt, failure, delay)
        self.check_dispatch()
        remaining = self.remaining()
        await _guard(_sleep(self.policy.sleeper, delay), self.call, remaining)
        refusal = self.limit_refusal(0)
        if refusal:
            return refusal
        if self.call.cancelled:
            raise asyncio.CancelledError()
        self.emit("retry_started", attempt, failure)
        return None

    def cancel(
        self, attempt: _Attempt, cause: BaseException, recorded: bool = False
    ) -> None:
        attempt.category, attempt.reason, attempt.cause = (
            "cancellation",
            "cancelled",
            cause,
        )
        failure = attempt.failure(self.policy)
        if not attempt.sent:
            attempt.identity = attempt.identity.model_copy(
                update={
                    "wire_attempt": attempt.identity.wire_attempt - 1,
                    "attempt_id": None,
                }
            )
            failure = attempt.failure(self.policy)
        if not recorded:
            if attempt.sent:
                self.history.append(failure)
            self.causes.append(cause)
            self.responses.append(attempt.raw)
            if attempt.sent:
                try:
                    self.emit("attempt_failed", attempt, failure)
                except _HookError as observer_error:
                    self.causes.append(observer_error.original)
                    self.responses.append(attempt.raw)
        else:
            # Cancellation during admission/backoff retains the original failed
            # attempt in history, and adds its typed terminal cause privately.
            self.causes.append(cause)
            self.responses.append(attempt.raw)
        try:
            self.emit("cancelled", attempt, failure)
        except _HookError as observer_error:
            self.causes.append(observer_error.original)
            self.responses.append(attempt.raw)
        raise self.error("cancelled", attempt, failure) from None


async def recover(
    url: str,
    body: bytes,
    headers: dict,
    timeout: Timeout,
    decode: Callable[[object], Result],
    policy: RecoveryPolicy,
    call: RecoveryCall,
    operation: Literal["ordinary", "structured", "streaming"],
) -> tuple[Result, RecoveryReport]:
    """Send immutable encoded bytes with explicit per-wire accounting and admission."""
    return await _Recovery(policy, call, operation).run(
        url, body, headers, timeout, decode
    )


def preparation_error(
    cause: BaseException, operation: Literal["ordinary", "structured", "streaming"]
) -> RecoveryError:
    """Represent a pre-dispatch failure without inventing a wire attempt."""
    identity = Identity(
        logical_request_id=str(uuid4()), attempt_id=None, wire_attempt=0
    )
    failure = Failure(
        operation=operation,
        category="protocol",
        identity=identity,
        acceptance="no",
        reason="invalid_configuration",
    )
    report = RecoveryReport(
        identity=identity,
        progress=Progress(),
        outcome="ineligible",
        final_failure=failure,
    )
    failure._original_cause = cause
    return RecoveryError(report, (cause,), (b"",))
