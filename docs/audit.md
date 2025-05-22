# Audit System

The Mojentic audit system provides observability into agentic interactions, allowing you to trace through the major events in your application such as LLM calls, tool usage, and agent interactions.

## Overview

The audit system is designed to be:
- **Non-intrusive**: It can be added to existing code with minimal changes
- **Configurable**: You can enable/disable auditing as needed
- **Extensible**: You can filter and query audit events in various ways
- **Comprehensive**: It captures key events across the system

## Key Components

### AuditEvent

The base class for all audit events, extending the core `Event` class. All audit events include:
- `source`: The type of the component that created the event
- `correlation_id`: A unique identifier for related events
- `timestamp`: When the event occurred

### Specific Audit Event Types

- **LLMCallAuditEvent**: Records when an LLM is called with specific messages
- **LLMResponseAuditEvent**: Records when an LLM responds to a call
- **ToolCallAuditEvent**: Records when a tool is called during agent execution
- **AgentInteractionAuditEvent**: Records interactions between agents

### EventStore

The `EventStore` class stores and manages audit events, providing methods to:
- Store events
- Filter events by type, time range, or custom filters
- Get the latest events
- Clear the event store

### AuditSystem

The central system for recording and querying audit events with convenient methods to:
- Record various types of events (LLM calls, tool usage, agent interactions)
- Query events with various filters
- Enable/disable auditing

## Adding Auditing to Your Application

The audit system integrates with key components:

1. **With LLMBroker**:
   ```python
   audit_system = AuditSystem()
   llm = LLMBroker("model-name", audit_system=audit_system)
   ```

2. **With Dispatcher**:
   ```python
   dispatcher = Dispatcher(router, audit_system=audit_system)
   ```

3. **With Tools**:
   ```python
   tool = SomeTool(audit_system=audit_system)
   # Or
   tool = SomeTool()
   tool.set_audit_system(audit_system)
   ```

## Querying Audit Events

Retrieve and filter audit events:

```python
# Get all audit events
all_events = audit_system.get_events()

# Filter by event type
llm_calls = audit_system.get_events(event_type=LLMCallAuditEvent)

# Filter by time range
recent_events = audit_system.get_events(
    start_time=time.time() - 3600,  # Events in the last hour
    end_time=time.time()
)

# Get the last N events of a specific type
last_tool_calls = audit_system.get_last_n_audit_events(
    n=5, 
    event_type=ToolCallAuditEvent
)

# Custom filtering
failed_calls = audit_system.get_events(
    filter_func=lambda e: isinstance(e, ToolCallAuditEvent) and "error" in str(e.result)
)
```

## Complete Example

See the full example in `src/_examples/audit_demo.py` for a demonstration of setting up and using the audit system.

```python
from mojentic.audit.audit_system import AuditSystem
from mojentic.llm.llm_broker import LLMBroker

# Create audit system
audit_system = AuditSystem()

# Create LLM broker with audit system
llm = LLMBroker("model-name", audit_system=audit_system)

# Set up router and dispatcher
router = Router({...})
dispatcher = Dispatcher(router, audit_system=audit_system)

# Later, query events
llm_calls = audit_system.get_events(event_type=LLMCallAuditEvent)
for event in llm_calls:
    print(f"LLM call to {event.model} at {datetime.fromtimestamp(event.timestamp)}")
```

## Audit System vs. Logging

While the audit system may seem similar to logging, they serve different purposes:

| Feature | Audit System | Logging |
|---------|--------------|---------|
| **Primary Audience** | End users & Developers | Developers |
| **Focus** | System behavior & interactions | Technical details & debugging |
| **Structure** | Strongly typed events | Free-form messages |
| **Query Capability** | Structured filtering & retrieval | Text search |
| **Use Case** | Troubleshooting prompts in agentic systems | Debugging code issues |

The audit system complements rather than replaces traditional logging, providing a higher-level view focused on agentic interactions.