import asyncio
import json
from typing import Any, Dict, List, Optional

import pytest

from mojentic.realtime.config import RealtimeVoiceConfig
from mojentic.realtime.openai_gateway import OpenAIRealtimeGateway
from mojentic.realtime.transport import RealtimeTransport, TransportListener


class _StubTransport(RealtimeTransport):
    """Scripted transport used to exercise the gateway without a network."""

    def __init__(self, scripted_messages: Optional[List[Dict[str, Any]]] = None):
        self.connected = False
        self.sent_payloads: List[Any] = []
        self.scripted_messages = scripted_messages or []
        self._listener: Optional[TransportListener] = None
        self._closed = False

    async def connect(self, listener: TransportListener) -> None:
        self._listener = listener
        self.connected = True
        listener.on_open()
        for message in self.scripted_messages:
            listener.on_message(json.dumps(message))
        listener.on_close("server")

    async def send(self, payload: Any) -> None:
        self.sent_payloads.append(payload)

    async def close(self) -> None:
        self._closed = True

    def is_closed(self) -> bool:
        return self._closed


class DescribeOpenAIRealtimeGateway:
    class DescribeConstruction:
        def should_require_api_key(self, monkeypatch):
            monkeypatch.delenv("OPENAI_API_KEY", raising=False)

            with pytest.raises(ValueError):
                OpenAIRealtimeGateway()

        def should_accept_explicit_api_key(self):
            gateway = OpenAIRealtimeGateway(api_key="sk-test")

            assert gateway is not None

    class DescribeOpen:
        def should_open_session_with_unique_id(self):
            transport = _StubTransport()
            gateway = OpenAIRealtimeGateway(
                api_key="sk-test",
                transport_factory=lambda url, headers, protocols: transport,
            )

            session = asyncio.run(
                gateway.open("gpt-realtime", RealtimeVoiceConfig(), correlation_id="cid-1")
            )

            assert session.session_id
            assert transport.connected

        def should_route_events_to_session_queue(self):
            scripted = [
                {"type": "session.created", "session": {"id": "sess_1"}},
                {"type": "rate_limits.updated", "rate_limits": [{"name": "tokens"}]},
            ]
            transport = _StubTransport(scripted_messages=scripted)
            gateway = OpenAIRealtimeGateway(
                api_key="sk-test",
                transport_factory=lambda url, headers, protocols: transport,
            )

            async def drain() -> List[Dict[str, Any]]:
                session = await gateway.open("gpt-realtime", RealtimeVoiceConfig())
                events = []
                async for event in session.events():
                    events.append(event)
                return events

            collected = asyncio.run(drain())

            assert [e["type"] for e in collected] == [
                "session.created",
                "rate_limits.updated",
            ]

        def should_surface_malformed_messages_as_errors(self):
            class _BadTransport(_StubTransport):
                async def connect(self, listener):  # type: ignore[override]
                    self._listener = listener
                    self.connected = True
                    listener.on_open()
                    listener.on_message("not-valid-json")
                    listener.on_close("server")

            transport = _BadTransport()
            gateway = OpenAIRealtimeGateway(
                api_key="sk-test",
                transport_factory=lambda url, headers, protocols: transport,
            )

            async def drain():
                session = await gateway.open("gpt-realtime", RealtimeVoiceConfig())
                events = []
                async for event in session.events():
                    events.append(event)
                return events

            collected = asyncio.run(drain())

            assert collected[0]["type"] == "error"
            assert collected[0]["error"]["type"] == "parse_error"
