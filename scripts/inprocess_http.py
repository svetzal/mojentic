"""Finite HTTP transport and virtual clock for source and installed-wheel proof.

The SDKs still encode requests and decode responses. Only httpx's network
transport is replaced; no client or Mojentic implementation is mocked.
"""

import asyncio
import socket
import time
from collections.abc import AsyncIterator, Awaitable, Callable, Iterator
from contextlib import contextmanager
from types import SimpleNamespace
from typing import TypeVar

import httpx
import httpx2

from mojentic.llm import stream_timing
from mojentic.llm.gateways.tokenizer_gateway import TokenizerGateway

Result = TypeVar("Result")
Chunk = tuple[float, bytes | BaseException]
ResponseData = bytes | BaseException | list[Chunk] | tuple[float, bytes]
Reply = tuple[int, dict[str, str], ResponseData]
Request = httpx.Request | httpx2.Request
CapturedRequest = tuple[str, bytes, httpx.Headers]


class VirtualClock:
    """Explicit, exact binary-fraction clock with no wall time dependency."""

    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


_socket_init = socket.socket.__init__


def no_internet_socket(
    self: socket.socket,
    family: int = socket.AF_INET,
    type: int = socket.SOCK_STREAM,
    proto: int = 0,
    fileno: int | None = None,
) -> None:
    if family in {socket.AF_INET, socket.AF_INET6}:
        forbidden_network()
    _socket_init(self, family, type, proto, fileno)


clock = VirtualClock()
_async_sleep = asyncio.sleep


async def yield_control(
    delay: float = 0, result: Result | None = None
) -> Result | None:
    """Cooperate with the event loop without a timer."""
    return await _async_sleep(0, result)


async def virtual_sleep(delay: float) -> None:
    """Model an explicitly requested retry wait on the injected clock."""
    clock.advance(delay)
    await yield_control()


def forbidden_sleep(*args: object, **kwargs: object) -> None:
    raise AssertionError("Verification must inject a sleeper instead of sleeping")


class Body(httpx.SyncByteStream, httpx.AsyncByteStream):
    def __init__(self, chunks: list[Chunk], headers: dict[str, str]) -> None:
        self.chunks = chunks
        self.headers = headers
        self.closed = False

    def __iter__(self) -> Iterator[bytes]:
        size = 0
        for delay, chunk in self.chunks:
            clock.advance(delay)
            if isinstance(chunk, BaseException):
                raise chunk
            size += len(chunk)
            yield chunk
        expected = self.headers.get("Content-Length")
        if expected is not None and size < int(expected):
            raise httpx.RemoteProtocolError("incomplete response body")

    async def __aiter__(self) -> AsyncIterator[bytes]:
        for chunk in self:
            yield chunk

    def close(self) -> None:
        self.closed = True

    async def aclose(self) -> None:
        self.close()


class Body2(httpx2.SyncByteStream, httpx2.AsyncByteStream):
    """Adapt the same scripted wire bytes to the SDK's httpx2 boundary."""

    def __init__(self, body: httpx.SyncByteStream | httpx.AsyncByteStream) -> None:
        self.body = body

    def __iter__(self) -> Iterator[bytes]:
        yield from self.body

    async def __aiter__(self) -> AsyncIterator[bytes]:
        async for chunk in self.body:
            yield chunk

    def close(self) -> None:
        self.body.close()

    async def aclose(self) -> None:
        await self.body.aclose()


@contextmanager
def replace(target: object, name: str, value: object) -> Iterator[None]:
    """Temporarily substitute one I/O boundary and always restore it."""
    previous = getattr(target, name)
    setattr(target, name, value)
    try:
        yield
    finally:
        setattr(target, name, previous)


def forbidden_network(*args: object, **kwargs: object) -> None:
    raise AssertionError("Verification must not open sockets or resolve services")


@contextmanager
def offline() -> Iterator[None]:
    """Fail immediately if any route escapes the in-process transport."""
    with (
        replace(socket.socket, "__init__", no_internet_socket),
        replace(asyncio, "sleep", yield_control),
        replace(time, "sleep", forbidden_sleep),
        replace(socket.socket, "connect", forbidden_network),
        replace(socket.socket, "connect_ex", forbidden_network),
        replace(socket, "getaddrinfo", forbidden_network),
        replace(socket.socket, "bind", forbidden_network),
    ):
        yield


@contextmanager
def transport(
    handler: Callable[[Request], httpx.Response | Awaitable[httpx.Response]],
) -> Iterator[None]:
    """Install an in-process HTTP boundary for sync and async SDK clients."""

    def send(_transport, request):
        return handler(request)

    async def send_async(_transport, request):
        result = handler(request)
        return await result if hasattr(result, "__await__") else result

    def send2(_transport, request):
        response = handler(request)
        return httpx2.Response(
            response.status_code,
            headers=response.headers,
            stream=Body2(response.stream),
        )

    async def send_async2(_transport, request):
        response = handler(request)
        if hasattr(response, "__await__"):
            response = await response
        return httpx2.Response(
            response.status_code,
            headers=response.headers,
            stream=Body2(response.stream),
        )

    with (
        offline(),
        replace(httpx2.HTTPTransport, "handle_request", send2),
        replace(httpx2.AsyncHTTPTransport, "handle_async_request", send_async2),
        replace(httpx.HTTPTransport, "handle_request", send),
        replace(httpx.AsyncHTTPTransport, "handle_async_request", send_async),
        replace(stream_timing, "time", SimpleNamespace(monotonic=clock)),
    ):
        yield


@contextmanager
def scripted_http(
    replies: list[Reply],
    *,
    timeouts: list[dict[str, float | None]] | None = None,
) -> Iterator[tuple[str, list[CapturedRequest]]]:
    """Capture exact bytes and authentication; return scripted wire responses."""
    requests = []
    clock.now = 0.0

    def respond(request):
        if timeouts is not None:
            timeouts.append(request.extensions["timeout"])
        headers = httpx.Headers(request.headers)
        requests.append((request.url.raw_path.decode(), request.content, headers))
        status, response_headers, data = replies[len(requests) - 1]
        if isinstance(data, BaseException):
            raise data
        delay, data = data if isinstance(data, tuple) else (0, data)
        chunks = data if isinstance(data, list) else [(delay, data)]
        return httpx.Response(
            status, headers=response_headers, stream=Body(chunks, response_headers)
        )

    with transport(respond):
        yield "http://provider.test", requests


class PendingBody(httpx.AsyncByteStream):
    """A suspended response; cancellation closes it without threads or timers."""

    def __init__(
        self,
        started: asyncio.Event,
        closed: asyncio.Event,
        initial: bytes | None = None,
    ) -> None:
        self.started = started
        self.closed = closed
        self.initial = initial

    async def __aiter__(self) -> AsyncIterator[bytes]:
        try:
            if self.initial is not None:
                yield self.initial
            self.started.set()
            await asyncio.Event().wait()
        finally:
            self.closed.set()

    async def aclose(self) -> None:
        self.closed.set()


@contextmanager
def unfinished_http(
    initial: bytes | None = None,
) -> Iterator[tuple[str, list[CapturedRequest], asyncio.Event, asyncio.Event]]:
    """Suspend at headers or after the first chunk, exposing cleanup events."""
    started, closed = asyncio.Event(), asyncio.Event()
    requests = []

    async def respond(request):
        requests.append(
            (
                request.url.raw_path.decode(),
                request.content,
                httpx.Headers(request.headers),
            )
        )
        if initial is None:
            started.set()
            try:
                await asyncio.Event().wait()
            finally:
                closed.set()
        return httpx.Response(200, stream=PendingBody(started, closed, initial))

    with transport(respond):
        yield "http://provider.test", requests, started, closed


class InProcessTokenizer(TokenizerGateway):
    """Deterministic tokenizer gateway for tests that do not specify token math."""

    def __init__(self) -> None:
        pass

    def encode(self, text: str) -> list[int]:
        return [ord(character) for character in text]

    def decode(self, tokens: list[int]) -> str:
        return "".join(chr(token) for token in tokens)
