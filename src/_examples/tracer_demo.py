"""
Example script demonstrating the tracer system's printable_summary functionality.

This simplified version demonstrates the printable_summary method of tracer events.
"""
import time
from datetime import datetime

from mojentic.tracer.tracer_events import (
    TracerEvent,
    LLMCallTracerEvent,
    LLMResponseTracerEvent,
    ToolCallTracerEvent,
    AgentInteractionTracerEvent
)
from mojentic.tracer.tracer_system import TracerSystem


# Define a class to use as source for events
class DemoSource:
    """Demo source class for tracer events."""
    pass


def create_sample_events():
    """Create sample tracer events for demonstration."""
    now = time.time()
    source = DemoSource
    
    events = [
        LLMCallTracerEvent(
            source=source,
            timestamp=now - 10,
            model="gpt-4",
            messages=[{"role": "user", "content": "What time is it?"}],
            temperature=0.7
        ),
        LLMResponseTracerEvent(
            source=source,
            timestamp=now - 9,
            model="gpt-4",
            content="The current time depends on your location. I don't have access to your device's time.",
            call_duration_ms=1200.5
        ),
        ToolCallTracerEvent(
            source=source,
            timestamp=now - 8,
            tool_name="current_datetime",
            arguments={},
            result="2025-05-22 12:45:00",
            caller="ChatAgent"
        ),
        AgentInteractionTracerEvent(
            source=source,
            timestamp=now - 7,
            from_agent="ChatAgent",
            to_agent="OutputAgent",
            event_type="ResponseEvent",
            event_id="abc123"
        )
    ]
    
    return events


def print_tracer_events(events):
    """Print tracer events using their printable_summary method."""
    print(f"\n{'-'*80}")
    print("Tracer Events:")
    print(f"{'-'*80}")
    
    for i, event in enumerate(events, 1):
        print(f"{i}. {event.printable_summary()}")
        print()


def main():
    """Run the tracer demo."""
    # Create a tracer system and populate it with sample events
    tracer = TracerSystem()
    sample_events = create_sample_events()
    
    # Store the events in the tracer system
    for event in sample_events:
        tracer.record_event(event)
    
    # Print the events
    print("Demonstrating the printable_summary method of tracer events")
    events = tracer.get_events()
    print_tracer_events(events)


if __name__ == "__main__":
    main()