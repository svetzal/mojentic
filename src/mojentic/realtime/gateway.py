"""
Realtime voice gateway interface.

Sibling to :class:`mojentic.llm.gateways.llm_gateway.LLMGateway`: where
the chat-completions gateway exposes a request/response surface, this
one exposes a duplex session. The gateway is intentionally thin — own
the transport, validate events at the boundary, do no orchestration.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, AsyncIterator, Dict, Optional

from mojentic.realtime.config import RealtimeVoiceConfig


class RealtimeGatewaySession(ABC):
    """
    Live duplex session opened by a :class:`RealtimeVoiceGateway`.

    ``events`` yields server events in arrival order, terminating when
    the session closes. ``send_event`` queues a client event. ``close``
    is idempotent.
    """

    @property
    @abstractmethod
    def session_id(self) -> str:
        ...

    @abstractmethod
    async def send_event(self, event: Dict[str, Any]) -> None:
        ...

    @abstractmethod
    def events(self) -> AsyncIterator[Dict[str, Any]]:
        ...

    @abstractmethod
    async def close(self) -> None:
        ...

    @abstractmethod
    def is_closed(self) -> bool:
        ...


class RealtimeVoiceGateway(ABC):
    """
    Open duplex realtime sessions against a provider.

    Implementations are intentionally thin: own the transport, validate
    events at the boundary, do no orchestration.
    """

    @abstractmethod
    async def open(
        self,
        model: str,
        config: RealtimeVoiceConfig,
        correlation_id: Optional[str] = None,
    ) -> RealtimeGatewaySession:
        ...
