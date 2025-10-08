# Tracer Qt Viewer Example

This example demonstrates how to build a real-time visualization tool for Mojentic's tracer system using a Qt GUI.

## Overview

The `tracer_qt_viewer.py` script creates a Qt-based application that:
- Displays tracer events in real-time as they occur
- Shows events in a color-coded table with timestamps
- Allows clicking on events to see detailed information
- Demonstrates how to use EventStore callbacks for real-time monitoring
- Provides an example of building external observability tools

## Requirements

This example requires PyQt6, which is not included in Mojentic's core dependencies:

```bash
pip install PyQt6
```

## Usage

Run the viewer:

```bash
python tracer_qt_viewer.py
```

This will:
1. Open a Qt window with a real-time event viewer
2. Display a table showing tracer events as they occur
3. Allow you to click "Run Test Query" to generate sample events
4. Let you click on any event to see detailed information

## Features

### Real-time Event Display
- Events appear in the table immediately as they're recorded
- Color-coded by event type (LLM calls, responses, tool calls, agent interactions)
- Shows timestamp, event type, correlation ID, summary, and duration

### Event Details Panel
- Click any event row to see full details
- View complete messages, arguments, and results
- Examine correlation IDs for request tracing

### Controls
- **Run Test Query**: Executes a sample LLM query with tools to generate events
- **Clear Events**: Clears the display and resets the tracer

## Architecture

This example demonstrates key observability patterns:

1. **EventStore Callback**: Uses `on_store_callback` to receive events in real-time
2. **Qt Signal/Slot**: Thread-safe event handling with Qt signals
3. **Event Filtering**: Color-codes and summarizes different event types
4. **Detailed Inspection**: Shows complete event data on demand

## Extending This Example

You can extend this viewer to:
- Filter events by type or correlation ID
- Export events to files or databases
- Add charts/graphs for performance metrics
- Stream events to external monitoring systems
- Add search and filtering capabilities
- Display event relationships (correlation chains)

## Integration with Your Code

To use the tracer in your own code:

```python
from mojentic.tracer import TracerSystem, EventStore

# Create EventStore with callback
def my_callback(event):
    # Handle event in real-time
    print(f"Event: {event}")

event_store = EventStore(on_store_callback=my_callback)
tracer = TracerSystem(event_store=event_store)

# Use tracer with your LLM broker, tools, etc.
llm = LLMBroker("model-name", tracer=tracer)
```

## See Also

- `tracer_demo.py` - Console-based tracer example
- `docs/observable.md` - Complete observability documentation
- `simple_tool.py` - Simple agent/tool example without tracer
