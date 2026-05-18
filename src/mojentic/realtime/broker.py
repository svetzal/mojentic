"""
Realtime voice broker — sibling to :class:`mojentic.llm.llm_broker.LLMBroker`
for duplex voice + tool sessions.
"""
from __future__ import annotations

import uuid
from typing import Any, Dict, Optional

from mojentic.llm.tools.runner import AsyncParallelToolRunner, ToolRunner
from mojentic.realtime.config import RealtimeVoiceConfig
from mojentic.realtime.gateway import RealtimeVoiceGateway
from mojentic.realtime.session import RealtimeSession
from mojentic.tracer.tracer_system import TracerSystem


class RealtimeVoiceBroker:
    """
    Long-lived broker that opens duplex realtime sessions against a gateway.

    The broker itself holds no session state — it is reusable across
    many concurrent sessions. The :class:`RealtimeSession` returned by
    :meth:`connect` owns the socket lifetime.

    Mirrors the TypeScript ``RealtimeVoiceBroker`` so the cross-port
    surface stays familiar.
    """

    def __init__(
        self,
        model: str,
        gateway: RealtimeVoiceGateway,
        config: Optional[RealtimeVoiceConfig] = None,
        tracer: Optional[TracerSystem] = None,
        tool_runner: Optional[ToolRunner] = None,
    ):
        self._model = model
        self._gateway = gateway
        self._config = config or RealtimeVoiceConfig()
        self._tracer = tracer
        self._tool_runner: ToolRunner = tool_runner or AsyncParallelToolRunner()

    @property
    def model(self) -> str:
        return self._model

    @property
    def gateway(self) -> RealtimeVoiceGateway:
        return self._gateway

    async def connect(
        self, overrides: Optional[Dict[str, Any]] = None
    ) -> RealtimeSession:
        """
        Open a new realtime session.

        The session is fully initialised (initial ``session.update``
        sent) before returning so callers can immediately pipe audio
        or send text.

        ``overrides`` is a dict of :class:`RealtimeVoiceConfig` fields
        to merge over the broker-level config for this one session.
        Tools and provider_extras merge with sensible precedence.
        """
        merged = self._merge_config(overrides or {})
        correlation_id = str(uuid.uuid4())

        gateway_session = await self._gateway.open(self._model, merged, correlation_id)

        session = RealtimeSession(
            gateway_session,
            config=merged,
            tool_runner=self._tool_runner,
            tracer=self._tracer,
            correlation_id=correlation_id,
        )
        try:
            await session.initialise()
        except Exception:
            await session.close()
            raise
        return session

    def _merge_config(self, overrides: Dict[str, Any]) -> RealtimeVoiceConfig:
        base = self._config.model_dump()
        merged: Dict[str, Any] = {**base, **overrides}

        # Tools are objects, not dump-friendly — re-attach the explicit list.
        merged["tools"] = overrides.get("tools", self._config.tools)

        # Merge provider_extras dictionaries.
        base_extras = self._config.provider_extras or {}
        override_extras = overrides.get("provider_extras") or {}
        if base_extras or override_extras:
            merged["provider_extras"] = {**base_extras, **override_extras}

        return RealtimeVoiceConfig(**merged)
