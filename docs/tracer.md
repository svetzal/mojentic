# Tracer System

The Mojentic tracer system provides observability into agentic interactions, allowing you to trace through the major events in your application such as LLM calls, tool usage, and agent interactions.

## Overview

The tracer system is designed to be:
- **Non-intrusive**: It can be added to existing code with minimal changes
- **Configurable**: You can enable/disable tracing as needed
- **Extensible**: You can filter and query tracer events in various ways
- **Comprehensive**: It captures key events across the system

## Key Components

### TracerEvent

The base class for all tracer events, extending the core `Event` class. All tracer events include:
- `source`: The type of the component that created the event
- `correlation_id`: A unique identifier for related events
- `timestamp`: When the event occurred

### Specific Tracer Event Types

- **LLMCallTracerEvent**: Records when an LLM is called with specific messages
- **LLMResponseTracerEvent**: Records when an LLM responds to a call
- **ToolCallTracerEvent**: Records when a tool is called during agent execution
- **AgentInteractionTracerEvent**: Records interactions between agents

### EventStore

The `EventStore` class stores and manages tracer events, providing methods to:
- Store events
- Filter events by type, time range, or custom filters
- Get the latest events
- Clear the event store

### TracerSystem

The central system for recording and querying tracer events with convenient methods to:
- Record various types of events (LLM calls, tool usage, agent interactions)
- Query events with various filters
- Enable/disable tracing

## Adding Tracing to Your Application

The tracer system integrates with key components:

1. **With LLMBroker**:
   ```python
   tracer_system = TracerSystem()
   llm = LLMBroker("model-name", tracer=tracer_system)
   ```

2. **With Dispatcher**:
   ```python
   dispatcher = Dispatcher(router, tracer=tracer_system)
   ```

3. **With Tools**:
   ```python
   tool = SomeTool(tracer=tracer_system)
   # Or
   tool = SomeTool()
   tool.set_tracer_system(tracer_system)
   ```

## Querying Tracer Events

Retrieve and filter tracer events:

```python
# Get all tracer events
all_events = tracer_system.get_events()

# Filter by event type
llm_calls = tracer_system.get_events(event_type=LLMCallTracerEvent)

# Filter by time range
recent_events = tracer_system.get_events(
    start_time=time.time() - 3600,  # Events in the last hour
    end_time=time.time()
)

# Get the last N events of a specific type
last_tool_calls = tracer_system.get_last_n_tracer_events(
    n=5, 
    event_type=ToolCallTracerEvent
)

# Custom filtering
failed_calls = tracer_system.get_events(
    filter_func=lambda e: isinstance(e, ToolCallTracerEvent) and "error" in str(e.result)
)
```

## Complete Example

See the full example in `src/_examples/tracer_demo.py` for a demonstration of setting up and using the tracer system.

```python
from mojentic.tracer.tracer_system import TracerSystem
from mojentic.llm.llm_broker import LLMBroker

# Create tracer system
tracer_system = TracerSystem()

# Create LLM broker with tracer system
llm = LLMBroker("model-name", tracer=tracer_system)

# Set up router and dispatcher
router = Router({...})
dispatcher = Dispatcher(router, tracer=tracer_system)

# Later, query events
llm_calls = tracer_system.get_events(event_type=LLMCallTracerEvent)
for event in llm_calls:
    print(f"LLM call to {event.model} at {datetime.fromtimestamp(event.timestamp)}")
```

## Tracer System vs. Logging

While the tracer system may seem similar to logging, they serve different purposes:

| Feature | Tracer System | Logging |
|---------|--------------|---------|
| **Primary Audience** | End users & Developers | Developers |
| **Focus** | System behavior & interactions | Technical details & debugging |
| **Structure** | Strongly typed events | Free-form messages |
| **Query Capability** | Structured filtering & retrieval | Text search |
| **Use Case** | Troubleshooting prompts in agentic systems | Debugging code issues |

The tracer system complements rather than replaces traditional logging, providing a higher-level view focused on agentic interactions.