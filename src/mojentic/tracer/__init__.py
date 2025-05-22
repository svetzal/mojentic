
"""
Mojentic tracer module for tracking system operations.
"""
from mojentic.tracer.tracer_events import (
    TracerEvent,
    LLMCallTracerEvent,
    LLMResponseTracerEvent,
    ToolCallTracerEvent,
    AgentInteractionTracerEvent
)
from mojentic.tracer.tracer_system import TracerSystem
from mojentic.tracer.null_tracer import NullTracer

# Create a singleton NullTracer instance for use throughout the application
null_tracer = NullTracer()