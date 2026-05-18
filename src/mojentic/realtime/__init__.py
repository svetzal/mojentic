"""
Realtime voice subsystem.

Sibling to :mod:`mojentic.llm` — exposes a :class:`RealtimeVoiceBroker`
that opens duplex voice + tool sessions against a realtime-capable
provider (currently OpenAI). Mirrors the TypeScript implementation in
``mojentic-ts`` so consumers of either port see the same conceptual API.
"""

from mojentic.realtime.config import (
    REALTIME_DEFAULTS,
    InterruptOutputPolicy,
    RealtimeAudioFormat,
    RealtimeModality,
    RealtimeToolChoice,
    RealtimeVoice,
    RealtimeVoiceConfig,
    SemanticVadConfig,
    ServerVadConfig,
    TurnDetectionMode,
)
from mojentic.realtime.events import (
    RealtimeEvent,
    RealtimeItem,
    TokenUsage,
)
from mojentic.realtime.gateway import RealtimeGatewaySession, RealtimeVoiceGateway
from mojentic.realtime.openai_gateway import OpenAIRealtimeGateway
from mojentic.realtime.transport import RealtimeTransport, WebSocketTransport

__all__ = [
    "InterruptOutputPolicy",
    "OpenAIRealtimeGateway",
    "REALTIME_DEFAULTS",
    "RealtimeAudioFormat",
    "RealtimeEvent",
    "RealtimeGatewaySession",
    "RealtimeItem",
    "RealtimeModality",
    "RealtimeToolChoice",
    "RealtimeTransport",
    "RealtimeVoice",
    "RealtimeVoiceConfig",
    "RealtimeVoiceGateway",
    "SemanticVadConfig",
    "ServerVadConfig",
    "TokenUsage",
    "TurnDetectionMode",
    "WebSocketTransport",
]
