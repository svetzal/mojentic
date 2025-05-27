# mojentic: Using the Mojentic Library

Mojentic is an agentic framework that provides a simple and flexible way to assemble teams of agents to solve complex problems. It supports integration with various LLM providers (Ollama, OpenAI, Anthropic) and includes tools for task automation.

## Core Components

### LLMBroker

The central component for interacting with language models:

```python
from mojentic.llm import LLMBroker

# Create a broker with a specific model
llm_broker = LLMBroker(model="llama3.3-70b-32k")  # Uses Ollama by default

# For OpenAI models
from mojentic.llm.gateways.openai import OpenAIGateway
llm_broker = LLMBroker(model="gpt-4-turbo", gateway=OpenAIGateway())
```

Use the broker to generate responses:

```python
from mojentic.llm.gateways.models import LLMMessage, MessageRole

# Generate a text response
messages = [
    LLMMessage(role=MessageRole.System, content="You are a helpful assistant."),
    LLMMessage(role=MessageRole.User, content="What is the capital of France?")
]
response = llm_broker.generate(messages)

# Generate a structured response
from pydantic import BaseModel

class CapitalInfo(BaseModel):
    country: str
    capital: str
    population: int

structured_response = llm_broker.generate_object(messages, object_model=CapitalInfo)
print(structured_response.capital)  # "Paris"
```

You can also get a list of available models from any LLM gateway implementation:

```python
from mojentic.llm.gateways import OllamaGateway, OpenAIGateway
from mojentic.llm.gateways.anthropic import AnthropicGateway
import os

# List Ollama models
ollama = OllamaGateway()
ollama_models = ollama.get_available_models()
print("Available Ollama models:", ollama_models)

# List OpenAI models
openai = OpenAIGateway(os.environ["OPENAI_API_KEY"])
openai_models = openai.get_available_models()
print("Available OpenAI models:", openai_models)

# List Anthropic models
anthropic = AnthropicGateway(os.environ["ANTHROPIC_API_KEY"])
anthropic_models = anthropic.get_available_models()
print("Available Anthropic models:", anthropic_models)
```

### ChatSession

Manages stateful conversations with automatic context management:

```python
from mojentic.llm import ChatSession, LLMBroker

llm_broker = LLMBroker(model="llama3.3-70b-32k")
chat_session = ChatSession(
    llm_broker,
    system_prompt="You are a helpful assistant specialized in geography.",
    max_context=16384  # Automatically manages context window
)

response = chat_session.send("What is the capital of France?")
follow_up = chat_session.send("What is its population?")  # Maintains conversation context
```

### Tools

Extend LLM capabilities with specialized tools:

```python
from mojentic.llm import ChatSession, LLMBroker
from mojentic.llm.tools.date_resolver import ResolveDateTool

# Create a chat session with a tool
llm_broker = LLMBroker(model="llama3.3-70b-32k")
chat_session = ChatSession(llm_broker, tools=[ResolveDateTool()])

# The LLM can now resolve relative dates
response = chat_session.send("What date is next Monday?")
```

Create custom tools by extending LLMTool:

```python
from mojentic.llm.tools.llm_tool import LLMTool

class WeatherTool(LLMTool):
    def run(self, location: str):
        # Implement weather lookup logic
        return {"temperature": 22, "conditions": "sunny"}

    @property
    def descriptor(self):
        return {
            "type": "function",
            "function": {
                "name": "get_weather",
                "description": "Get current weather for a location",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "location": {
                            "type": "string",
                            "description": "City or location name"
                        }
                    },
                    "required": ["location"]
                }
            }
        }
```

### Agents

Create agents with different capabilities:

```python
from mojentic.agents import BaseLLMAgent
from mojentic.llm import LLMBroker

llm_broker = LLMBroker(model="llama3.3-70b-32k")
agent = BaseLLMAgent(
    llm_broker,
    behaviour="You are a helpful assistant specialized in geography."
)

response = agent.generate_response("What is the capital of France?")
```

Agents with memory:

```python
from mojentic.agents import BaseLLMAgentWithMemory
from mojentic.context.shared_working_memory import SharedWorkingMemory
from pydantic import BaseModel

class Response(BaseModel):
    answer: str

memory = SharedWorkingMemory()
agent = BaseLLMAgentWithMemory(
    llm_broker,
    memory=memory,
    behaviour="You are a helpful assistant.",
    instructions="Answer the user's question.",
    response_model=Response
)

# Agent will remember information across interactions
response = agent.generate_response("My name is Alice.")
response = agent.generate_response("What's my name?")  # Will know the name is Alice
```

### Tracer

Monitor and analyze interactions with LLMs and tools for debugging and observability:

```python
from mojentic.tracer import TracerSystem
from mojentic.tracer.tracer_events import (
    LLMCallTracerEvent, 
    LLMResponseTracerEvent, 
    ToolCallTracerEvent,
    AgentInteractionTracerEvent
)
from mojentic.llm import LLMBroker, ChatSession
from mojentic.llm.tools.date_resolver import ResolveDateTool

# Create a tracer system
tracer = TracerSystem()

# Integrate with LLMBroker
llm_broker = LLMBroker(model="llama3.3-70b-32k", tracer=tracer)

# Integrate with tools
date_tool = ResolveDateTool(llm_broker=llm_broker, tracer=tracer)

# Create a chat session with the broker and tool
chat_session = ChatSession(llm_broker, tools=[date_tool])

# Use the chat session normally
response = chat_session.send("What day is next Friday?")

# Retrieve and analyze traced events
all_events = tracer.get_events()
print(f"Total events recorded: {len(all_events)}")

# Filter events by type
llm_calls = tracer.get_events(event_type=LLMCallTracerEvent)
llm_responses = tracer.get_events(event_type=LLMResponseTracerEvent)
tool_calls = tracer.get_events(event_type=ToolCallTracerEvent)
agent_interactions = tracer.get_events(event_type=AgentInteractionTracerEvent)

# Get the last few events
last_events = tracer.get_last_n_tracer_events(3)

# Filter events by time range
start_time = 1625097600.0  # Unix timestamp
end_time = 1625184000.0    # Unix timestamp
time_filtered_events = tracer.get_events(start_time=start_time, end_time=end_time)

# Print event summaries
for event in last_events:
    print(event.printable_summary())

# Extract specific information from events
if tool_calls:
    tool_usage = {}
    for event in tool_calls:
        tool_name = event.tool_name
        tool_usage[tool_name] = tool_usage.get(tool_name, 0) + 1

    print("Tool usage frequency:")
    for tool_name, count in tool_usage.items():
        print(f"  - {tool_name}: {count} calls")
```

#### Tracer Event Types

The tracer system captures different types of events:

1. **LLMCallTracerEvent**: Records when an LLM is called
   - `model`: The LLM model used
   - `messages`: The messages sent to the LLM
   - `temperature`: The temperature setting used
   - `tools`: The tools available to the LLM

2. **LLMResponseTracerEvent**: Records when an LLM responds
   - `model`: The LLM model used
   - `content`: The content of the response
   - `tool_calls`: Any tool calls made by the LLM
   - `call_duration_ms`: Duration of the call in milliseconds

3. **ToolCallTracerEvent**: Records tool usage
   - `tool_name`: Name of the tool called
   - `arguments`: Arguments provided to the tool
   - `result`: Result returned by the tool
   - `caller`: Component that called the tool

4. **AgentInteractionTracerEvent**: Records agent interactions
   - `from_agent`: Agent sending the event
   - `to_agent`: Agent receiving the event
   - `event_type`: Type of event being processed
   - `event_id`: Unique identifier for the event

Each event has a `printable_summary()` method that formats the event information for display.

## Best Practices

1. **Model Selection**: Choose appropriate models for your task:
   - Smaller models for simple tasks (faster, cheaper)
   - Larger models for complex reasoning

2. **Context Management**: Use ChatSession for long conversations to automatically manage context window limits

3. **Structured Output**: Use `generate_object()` instead of parsing JSON manually

4. **Tools**: Extend capabilities with tools rather than complex prompting

5. **Memory**: Use BaseLLMAgentWithMemory when information needs to persist across interactions

6. **Tracing**: Use the TracerSystem to monitor and debug interactions with LLMs and tools

7. **Observable EventStore**: Use the EventStore's callback functionality to react to events in real-time:
   ```python
   from mojentic.tracer import TracerSystem
   from mojentic.tracer.event_store import EventStore
   from mojentic.tracer.tracer_events import LLMCallTracerEvent

   # Create a callback function to process events as they are stored
   def on_event_stored(event):
       if isinstance(event, LLMCallTracerEvent):
           print(f"LLM call to model {event.model} with {len(event.messages)} messages")

   # Create an EventStore with the callback
   event_store = EventStore(on_store_callback=on_event_stored)

   # Create a TracerSystem with the observable EventStore
   tracer = TracerSystem(event_store=event_store)

   # Now use the tracer as normal - your callback will be triggered for each event
   ```
