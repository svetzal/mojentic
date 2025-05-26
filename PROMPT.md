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

## Best Practices

1. **Model Selection**: Choose appropriate models for your task:
   - Smaller models for simple tasks (faster, cheaper)
   - Larger models for complex reasoning

2. **Context Management**: Use ChatSession for long conversations to automatically manage context window limits

3. **Structured Output**: Use `generate_object()` instead of parsing JSON manually

4. **Tools**: Extend capabilities with tools rather than complex prompting

5. **Memory**: Use BaseLLMAgentWithMemory when information needs to persist across interactions