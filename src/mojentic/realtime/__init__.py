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

__all__ = [
    "InterruptOutputPolicy",
    "REALTIME_DEFAULTS",
    "RealtimeAudioFormat",
    "RealtimeEvent",
    "RealtimeItem",
    "RealtimeModality",
    "RealtimeToolChoice",
    "RealtimeVoice",
    "RealtimeVoiceConfig",
    "SemanticVadConfig",
    "ServerVadConfig",
    "TokenUsage",
    "TurnDetectionMode",
]
