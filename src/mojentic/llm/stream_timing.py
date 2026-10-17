"""Monotonic client evidence for one logical streamed completion."""

import time
from collections.abc import Callable, Iterator
from contextvars import ContextVar
from functools import wraps
from typing import Literal

from pydantic import BaseModel, ConfigDict


class ClientTiming(BaseModel):
    """Client elapsed milliseconds, independent of provider-reported durations."""

    model_config = ConfigDict(frozen=True)
    time_to_first_token_ms: float | None = None
    first_token_kind: Literal["thinking", "content", "tool_call"] | None = None
    request_duration_ms: float | None = None


class StreamClock:
    """Start at first dispatch, observe raw frames, and retain time across retries."""

    def __init__(self) -> None:
        self.started: float | None = None
        self.first: float | None = None
        self.kind: str | None = None
        self.provider: dict = {}

    def dispatch(self) -> None:
        """Record the first actual send, after all pre-dispatch callbacks."""
        if self.started is None:
            self.started = time.monotonic()

    def observe(self, frame: object) -> None:
        """Choose thinking, content, then argument fragments within one wire frame."""
        if not isinstance(frame, dict):
            return
        if frame.get("model") == "keepalive":
            return
        self.provider.update(
            {
                key: frame[key]
                for key in (
                    "usage",
                    "total_duration",
                    "load_duration",
                    "prompt_eval_duration",
                    "eval_duration",
                    "prompt_eval_count",
                    "eval_count",
                )
                if frame.get(key) is not None
            }
        )
        if self.first is not None:
            return
        choices = frame.get("choices")
        choices = choices if isinstance(choices, list) else []
        messages = [frame.get("message") or {}] + [
            choice.get("delta") or {} for choice in choices if isinstance(choice, dict)
        ]
        messages = [message for message in messages if isinstance(message, dict)]
        kinds = {
            "thinking": any(
                _text(m.get("thinking")) or _text(m.get("reasoning_content"))
                for m in messages
            ),
            "content": any(_text(m.get("content")) for m in messages),
            "tool_call": any(_arguments_present(m) for m in messages),
        }
        self.kind = next((kind for kind, present in kinds.items() if present), None)
        if self.kind is not None and self.started is not None:
            self.first = time.monotonic()

    def observe_frames(self, frames: list[object]) -> None:
        """Observe complete frames in transport order before capture callbacks."""
        for frame in frames:
            self.observe(frame)
            if frame == "[DONE]" or (
                isinstance(frame, dict)
                and (frame.get("done") is True or frame.get("error") is not None)
            ):
                return

    def evidence(self) -> dict:
        """Return only measured evidence; unsent requests have no duration."""
        if self.started is None:
            return {}
        result = {"request_duration_ms": (time.monotonic() - self.started) * 1000}
        if self.first is not None:
            result |= {
                "time_to_first_token_ms": (self.first - self.started) * 1000,
                "first_token_kind": self.kind,
            }
        return result


# A scope is active only while advancing a synchronous gateway iterator. It never
# remains installed while the caller is paused, or leaks into another stream.
_current_clock: ContextVar[StreamClock | None] = ContextVar(
    "stream_clock", default=None
)


def recovery_clock() -> StreamClock:
    """Share the advancing public iterator's clock, or own an async call's clock."""
    return _current_clock.get() or StreamClock()


def dispatch_stream(request: object) -> None:
    """HTTP request hook: record dispatch without changing the request."""
    clock = _current_clock.get()
    if clock is not None:
        clock.dispatch()


def observe_stream(frame: object) -> None:
    """Observe a decoded provider frame before it is split into public chunks."""
    clock = _current_clock.get()
    if clock is not None:
        clock.observe(frame)


def timed_stream(method: Callable) -> Callable:
    """Attach terminal timing while preserving legacy content and error behavior."""

    @wraps(method)
    def measured(self, *args, **kwargs) -> Iterator:
        from mojentic.llm.gateways.stream_events import (
            CompletionMetadata,
            StreamCompleted,
            StreamError,
        )

        clock = StreamClock()
        stream = method(self, *args, **kwargs)
        self.last_stream_metrics = None
        terminal = False
        try:
            while True:
                scope = _current_clock.set(clock)
                try:
                    event = next(stream)
                except StopIteration:
                    break
                finally:
                    _current_clock.reset(scope)
                if isinstance(event, (StreamCompleted, StreamError)):
                    terminal = True
                    evidence = event.metadata
                    if clock.started is not None:
                        evidence = (evidence or CompletionMetadata()).model_copy(
                            update=clock.evidence()
                        )
                    self.last_stream_metrics = evidence
                    event = event.model_copy(update={"metadata": evidence})
                yield event
            if (
                not terminal
                and clock.started is not None
                and self.last_stream_metrics is None
            ):
                self.last_stream_metrics = CompletionMetadata(
                    metadata=clock.provider or None, **clock.evidence()
                )
        except Exception as error:
            self.last_stream_metrics = self.last_stream_metrics or getattr(
                error, "stream_metrics", None
            )
            self.last_stream_metrics = _snapshot(clock, self.last_stream_metrics)
            error.stream_metrics = self.last_stream_metrics
            raise
        finally:
            stream.close()
            if self.last_stream_metrics is None:
                self.last_stream_metrics = _snapshot(clock, None)

    return measured


def _snapshot(clock: StreamClock, previous: ClientTiming | None) -> ClientTiming | None:
    from mojentic.llm.gateways.stream_events import CompletionMetadata

    if clock.started is None:
        return previous
    if previous is not None:
        return previous.model_copy(update=clock.evidence())
    return CompletionMetadata(metadata=clock.provider or None, **clock.evidence())


def _text(value: object) -> bool:
    return isinstance(value, str) and bool(value)


def _arguments_present(message: dict) -> bool:
    legacy = message.get("function_call")
    if isinstance(legacy, dict) and _text(legacy.get("arguments")):
        return True
    calls = message.get("tool_calls")
    if not isinstance(calls, list):
        return False
    functions = [call.get("function") for call in calls if isinstance(call, dict)]
    return any(
        _text(function.get("arguments")) or isinstance(function.get("arguments"), dict)
        for function in functions
        if isinstance(function, dict)
    )
