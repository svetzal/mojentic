"""
Mojentic tracer module for tracking system operations.
"""

# Core tracer components
from .event_store import EventStore  # noqa: F401
from .null_tracer import NullTracer
from .tracer_system import TracerSystem  # noqa: F401

# Create a singleton NullTracer instance for use throughout the application
null_tracer = NullTracer()
