
"""
Mojentic tracer module for tracking system operations.
"""

# Core tracer components
from .tracer_system import TracerSystem
from .null_tracer import NullTracer
from .event_store import EventStore

# Tracer event types
from .tracer_events import (
    TracerEvent,
    LLMCallTracerEvent,
    LLMResponseTracerEvent,
    ToolCallTracerEvent,
    AgentInteractionTracerEvent
)

# Create a singleton NullTracer instance for use throughout the application
null_tracer = NullTracer()