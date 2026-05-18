"""
Transport abstraction for the realtime subsystem.

The gateway owns I/O against this interface so unit tests can replace
the live WebSocket with a scripted, deterministic transport. The
production implementation wraps the ``websockets`` library.
"""
from __future__ import annotations

import asyncio
import json
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Protocol, Sequence

import structlog

logger = structlog.get_logger()


class TransportListener(Protocol):
    """
    Listener interface for transport events.

    Implementations call these in arrival order; the gateway
    demultiplexes them into a normalised async iterable for callers.
    All methods are sync — they enqueue into the gateway's own buffer.
    """

    def on_open(self) -> None: ...

    def on_message(self, data: str) -> None: ...

    def on_close(self, reason: str, err: Optional[BaseException] = None) -> None: ...

    def on_error(self, err: BaseException) -> None: ...


class RealtimeTransport(ABC):
    """
    A duplex text-frame channel.

    Minimal surface so providers can swap a real WebSocket for SSE, HTTP
    long-poll, in-process loopback, etc. ``connect`` resolves once the
    channel is open; ``send`` queues a JSON-stringifiable payload; ``close``
    is idempotent.
    """

    @abstractmethod
    async def connect(self, listener: TransportListener) -> None:
        ...

    @abstractmethod
    async def send(self, payload: Any) -> None:
        ...

    @abstractmethod
    async def close(self) -> None:
        ...

    @abstractmethod
    def is_closed(self) -> bool:
        ...


class WebSocketTransport(RealtimeTransport):
    """
    Production transport — a thin wrapper over the ``websockets`` library.

    Does not own base64 framing: realtime audio is base64-inside-JSON,
    which is the codec module's concern. This class only stringifies
    outbound payloads and decodes inbound text frames.
    """

    def __init__(
        self,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        subprotocols: Optional[Sequence[str]] = None,
    ):
        self._url = url
        self._headers = headers or {}
        self._subprotocols = list(subprotocols) if subprotocols else None
        self._websocket: Any = None
        self._listener: Optional[TransportListener] = None
        self._closed = False
        self._pump_task: Optional[asyncio.Task] = None

    async def connect(self, listener: TransportListener) -> None:
        if self._websocket is not None:
            raise RuntimeError("Transport already connected")
        self._listener = listener

        try:
            import websockets
        except ImportError as exc:  # pragma: no cover - guarded by deps
            raise RuntimeError(
                "The 'websockets' package is required for WebSocketTransport. "
                "Install with: pip install websockets"
            ) from exc

        connect_kwargs: Dict[str, Any] = {"additional_headers": self._headers}
        if self._subprotocols:
            connect_kwargs["subprotocols"] = self._subprotocols

        self._websocket = await websockets.connect(self._url, **connect_kwargs)
        listener.on_open()
        self._pump_task = asyncio.create_task(self._pump(), name="realtime-ws-pump")

    async def _pump(self) -> None:
        assert self._websocket is not None
        assert self._listener is not None
        try:
            async for message in self._websocket:
                if self._closed:
                    return
                if isinstance(message, bytes):
                    message = message.decode("utf-8")
                self._listener.on_message(message)
        except Exception as err:  # noqa: BLE001 - transport errors surface upward
            if not self._closed:
                self._listener.on_error(err)
        finally:
            if not self._closed:
                self._closed = True
                self._listener.on_close("server")

    async def send(self, payload: Any) -> None:
        if self._websocket is None or self._closed:
            raise RuntimeError("Transport not open")
        data = json.dumps(payload)
        await self._websocket.send(data)

    async def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        if self._websocket is not None:
            try:
                await self._websocket.close()
            except Exception:  # noqa: BLE001
                logger.debug("websocket close raised", exc_info=True)
        if self._pump_task is not None:
            self._pump_task.cancel()
            try:
                await self._pump_task
            except (asyncio.CancelledError, Exception):  # noqa: BLE001
                pass
        if self._listener is not None:
            self._listener.on_close("client")

    def is_closed(self) -> bool:
        return self._closed
