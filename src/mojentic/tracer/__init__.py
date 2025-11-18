
"""
Mojentic tracer module for tracking system operations.
"""

# Core tracer components
from .null_tracer import NullTracer

# Tracer event types

# Create a singleton NullTracer instance for use throughout the application
null_tracer = NullTracer()
