"""
OpenAI Realtime API gateway.

Owns the WebSocket, validates server events at the boundary using
:func:`parse_server_event`, and forwards client events verbatim. No
tool orchestration, no audio decoding — those live in the broker /
session layer.
"""
from __future__ import annotations

import asyncio
import json
import os
import uuid
from typing import Any, AsyncIterator, Callable, Dict, List, Optional

import structlog

from mojentic.realtime.config import RealtimeVoiceConfig
from mojentic.realtime.gateway import RealtimeGatewaySession, RealtimeVoiceGateway
from mojentic.realtime.schemas import parse_server_event
from mojentic.realtime.transport import RealtimeTransport, TransportListener, WebSocketTransport

logger = structlog.get_logger()

DEFAULT_OPENAI_REALTIME_URL = "wss://api.openai.com/v1/realtime"


TransportFactory = Callable[[str, Dict[str, str], List[str]], RealtimeTransport]


class _OpenAIRealtimeSession(RealtimeGatewaySession):
    def __init__(self, session_id: str, transport: RealtimeTransport):
        self._session_id = session_id
        self._transport = transport
        self._queue: asyncio.Queue = asyncio.Queue()
        self._closed = False

    @property
    def session_id(self) -> str:
        return self._session_id

    def enqueue(self, event: Dict[str, Any]) -> None:
        try:
            self._queue.put_nowait(event)
        except asyncio.QueueFull:  # pragma: no cover - default queue is unbounded
            logger.warning("realtime event queue full; dropping", event_type=event.get("type"))

    def signal_end(self) -> None:
        if self._closed:
            return
        self._closed = True
        # Wake any waiter on events() with a sentinel.
        self._queue.put_nowait(_EOS)

    async def send_event(self, event: Dict[str, Any]) -> None:
        if self._closed:
            raise RuntimeError("Session is closed")
        await self._transport.send(event)

    async def events(self) -> AsyncIterator[Dict[str, Any]]:
        while True:
            item = await self._queue.get()
            if item is _EOS:
                return
            yield item

    async def close(self) -> None:
        if self._closed:
            return
        await self._transport.close()
        self.signal_end()

    def is_closed(self) -> bool:
        return self._closed


_EOS: Dict[str, Any] = {"__eos__": True}


class _SessionListener(TransportListener):
    """Bridges transport callbacks into the gateway session's queue."""

    def __init__(self, session: _OpenAIRealtimeSession):
        self._session = session

    def on_open(self) -> None:
        # Session is usable as soon as connect() resolves; nothing to do.
        return

    def on_message(self, data: str) -> None:
        try:
            raw = json.loads(data)
        except json.JSONDecodeError as err:
            self._session.enqueue({
                "type": "error",
                "error": {"type": "parse_error", "message": str(err)},
            })
            return
        parsed = parse_server_event(raw)
        self._session.enqueue(parsed)

    def on_close(self, reason: str, err: Optional[BaseException] = None) -> None:
        self._session.signal_end()

    def on_error(self, err: BaseException) -> None:
        self._session.enqueue({
            "type": "error",
            "error": {"type": "transport_error", "message": str(err)},
        })


class OpenAIRealtimeGateway(RealtimeVoiceGateway):
    """
    Gateway against OpenAI's Realtime API.

    Each ``open()`` call provisions a new WebSocket and a fresh session
    id. The returned :class:`RealtimeGatewaySession` is the only
    stateful surface.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        transport_factory: Optional[TransportFactory] = None,
    ):
        resolved_key = api_key or os.environ.get("OPENAI_API_KEY")
        if not resolved_key:
            raise ValueError(
                "OpenAIRealtimeGateway requires an api_key (or OPENAI_API_KEY env var)."
            )
        self._api_key = resolved_key
        self._base_url = base_url or DEFAULT_OPENAI_REALTIME_URL
        self._transport_factory: TransportFactory = transport_factory or _default_transport_factory

    async def open(
        self,
        model: str,
        config: RealtimeVoiceConfig,
        correlation_id: Optional[str] = None,
    ) -> RealtimeGatewaySession:
        # config currently informs only the upcoming session.update; the
        # gateway just opens the socket.
        del config

        from urllib.parse import quote

        url = f"{self._base_url}?model={quote(model)}"
        headers: Dict[str, str] = {"Authorization": f"Bearer {self._api_key}"}
        if correlation_id:
            headers["X-Correlation-Id"] = correlation_id

        # OpenAI also accepts auth via WebSocket subprotocols, which is the
        # fallback for environments where the WebSocket layer doesn't allow
        # custom headers. Sending both is safe — the server picks whichever
        # the active transport actually forwards.
        protocols = ["realtime", f"openai-insecure-api-key.{self._api_key}"]

        transport = self._transport_factory(url, headers, protocols)
        session = _OpenAIRealtimeSession(str(uuid.uuid4()), transport)
        listener = _SessionListener(session)
        await transport.connect(listener)
        return session


def _default_transport_factory(
    url: str, headers: Dict[str, str], protocols: List[str]
) -> RealtimeTransport:
    return WebSocketTransport(url, headers=headers, subprotocols=protocols)
