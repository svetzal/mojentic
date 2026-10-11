"""
Mojentic LLM module for interacting with Large Language Models.
"""

# Main LLM components
from .chat_session import ChatSession  # noqa: F401
from .completion_config import CompletionConfig, ResponseFormat  # noqa: F401

# Re-export gateway components at the LLM level
from .gateways.models import LLMGatewayResponse, LLMMessage, MessageRole  # noqa: F401
from .gateways.stream_events import (  # noqa: F401
    CompletionMetadata,
    StreamCompleted,
    StreamContent,
    StreamError,
    StreamErrorReason,
    StreamEvent,
)
from .llm_broker import LLMBroker  # noqa: F401
from .message_composers import FileTypeSensor, MessageBuilder  # noqa: F401
from .recovery_stream import (
    RecoveryStreamEvent as RecoveryStreamEvent,
)
from .recovery_stream import (
    StreamFrameProgress as StreamFrameProgress,
)
from .recovery_stream import (
    StreamMetrics as StreamMetrics,
)
from .recovery_stream import (
    StreamOutcome as StreamOutcome,
)
from .registry.llm_registry import LLMRegistry  # noqa: F401

# Preserve the existing wildcard surface while declaring the additive exports.
__all__ = [
    "RecoveryStreamEvent",
    "StreamFrameProgress",
    "StreamMetrics",
    "StreamOutcome",
]
__all__ += [
    name for name in globals() if not name.startswith("_") and name not in __all__
]
