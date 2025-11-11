# Getting Started with Mojentic API Layer 1

This guide will help you get started with building projects using Mojentic's API Layer 1, which provides abstractions for working with Large Language Models (LLMs). By the end of this guide, you'll understand how to use the core components of Layer 1 and be able to build your own applications with Mojentic.

## Introduction to API Layer 1

API Layer 1 is focused on abstracting the functionality of Large Language Models (LLMs), allowing you to work with prompting, output generation, and tool use without being tied to a specific LLM implementation, its calling conventions, or library quirks.

The key components of this layer include:

- **LLMBroker**: The main entry point for interacting with LLMs
- **MessageBuilder**: A convenient way to construct rich prompt messages for LLMs that include images or text files
- **ChatSession**: A conversational interface with context management
- **LLM Gateways**: Adapters for specific LLM providers (Ollama, OpenAI)
- **Tools**: Utilities that extend LLM capabilities

## Prerequisites

Before you begin, make sure you have:

1. Python 3.11 or higher installed
2. Mojentic installed: `pip install mojentic`
3. Access to an LLM provider (Ollama or OpenAI)
   - For Ollama: Install [Ollama](https://ollama.ai/) locally
   - For OpenAI: Get an API key from [OpenAI](https://platform.openai.com/)

## Examples: From Simple to Complex

Let's explore how to use Mojentic's API Layer 1 with examples ranging from simple to complex.

### 1. Basic Text Generation

The simplest way to use Mojentic is to generate text responses using an LLM:

```python
from mojentic.llm.llm_broker import LLMBroker
from mojentic.llm.gateways.models import LLMMessage

# Create an LLMBroker with a default model (uses Ollama)
llm = LLMBroker(model="phi4:14b")

# Generate a simple text response
response = llm.generate(messages=[LLMMessage(content="Hello, how are you?")])
print(response)
```

If you prefer to use OpenAI models:

```python
import os
from mojentic.llm.gateways.openai import OpenAIGateway
from mojentic.llm.llm_broker import LLMBroker
from mojentic.llm.gateways.models import LLMMessage

# Create an LLMBroker with OpenAI
api_key = os.getenv("OPENAI_API_KEY")
gateway = OpenAIGateway(api_key)
llm = LLMBroker(model="gpt-4o", gateway=gateway)

# Generate a simple text response
response = llm.generate(messages=[LLMMessage(content="Hello, how are you?")])
print(response)
```

### 2. Structured Output Generation

Often, you'll want to get structured data back from an LLM. Mojentic makes this easy with Pydantic models:

```python
from pydantic import BaseModel, Field
from mojentic.llm.llm_broker import LLMBroker
from mojentic.llm.gateways.models import LLMMessage

# Define a Pydantic model for the output
class Sentiment(BaseModel):
    label: str = Field(..., title="Sentiment", description="Label for the sentiment (positive, negative, neutral)")
    confidence: float = Field(..., title="Confidence", description="Confidence score between 0 and 1")

# Create an LLMBroker
llm = LLMBroker(model="qwen3:32b")

# Generate structured output
result = llm.generate_object(
    messages=[LLMMessage(content="I absolutely loved the movie!")], 
    object_model=Sentiment
)

print(f"Sentiment: {result.label}, Confidence: {result.confidence}")
```

### 3. Using Tools with LLMs

Mojentic allows you to extend LLM capabilities with tools:

```python
from mojentic.llm.llm_broker import LLMBroker
from mojentic.llm.gateways.models import LLMMessage
from mojentic.llm.tools.date_resolver import ResolveDateTool

# Create an LLMBroker
llm = LLMBroker(model="qwen3:32b")

# Use a tool to resolve dates
result = llm.generate(
    messages=[LLMMessage(content="What is the date next Friday?")],
    tools=[ResolveDateTool()]
)

print(result)
```

### 4. Building a Simple Chat Interface

For conversational applications, use the ChatSession class:

```python
from mojentic.llm import ChatSession, LLMBroker

# Create an LLMBroker
llm_broker = LLMBroker(model="qwen3:32b")

# Create a ChatSession
chat_session = ChatSession(llm_broker)

# Simple chat loop
while True:
    query = input("You: ")
    if not query:
        break

    response = chat_session.send(query)
    print(f"AI: {response}")
```

### 5. Chat Interface with Tools

Enhance your chat interface with tools:

```python
from mojentic.llm import ChatSession, LLMBroker
from mojentic.llm.tools.date_resolver import ResolveDateTool

# Create an LLMBroker
llm_broker = LLMBroker(model="qwen3:32b")

# Create a ChatSession with a tool
chat_session = ChatSession(llm_broker, tools=[ResolveDateTool()])

# Chat loop
while True:
    query = input("You: ")
    if not query:
        break

    response = chat_session.send(query)
    print(f"AI: {response}")
```

### 6. Advanced: Custom Tools and Problem Solving

For more complex applications, you can create custom tools and use advanced problem-solving capabilities:

```python
from typing import List
from mojentic.agents import IterativeProblemSolver
from mojentic.llm import LLMBroker, ChatSession
from mojentic.llm.tools.date_resolver import ResolveDateTool
from mojentic.llm.tools.llm_tool import LLMTool


# Define a custom tool for iterative problem solving
class IterativeProblemSolverTool(LLMTool):
    def __init__(self, llm: LLMBroker, tools: List[LLMTool]):
        self.llm = llm
        self.tools = tools

    def run(self, problem_to_solve: str):
        solver = IterativeProblemSolver(
            llm=self.llm,
            available_tools=self.tools
        )
        return solver.solve(problem_to_solve)

    @property
    def descriptor(self):
        return {
            "type": "function",
            "function": {
                "name": "iterative_problem_solver",
                "description": "Iteratively solve a complex multi-step problem using available tools.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "problem_to_solve": {
                            "type": "string",
                            "description": "The problem or request to be solved.",
                        }
                    },
                    "required": ["problem_to_solve"],
                    "additionalProperties": False
                }
            }
        }


# Create an LLMBroker
llm = LLMBroker(model="qwen3:32b")

# Create a ChatSession with the custom tool
chat_session = ChatSession(
    llm,
    tools=[IterativeProblemSolverTool(llm=llm, tools=[ResolveDateTool()])]
)

# Chat loop
while True:
    query = input("You: ")
    if not query:
        break

    response = chat_session.send(query)
    print(f"AI: {response}")
```

### 7. Working with Images

If you need to analyze images, Mojentic supports multimodal models:

```python
from pathlib import Path
from mojentic.llm.llm_broker import LLMBroker
from mojentic.llm.gateways.models import LLMMessage

# Create an LLMBroker with an image-capable model
llm = LLMBroker(model="gemma3")  # For Ollama
# Or for OpenAI: llm = LLMBroker(model="gpt-4o", gateway=OpenAIGateway(api_key))

# Analyze an image
result = llm.generate(
    messages=[
        LLMMessage(
            content="Describe what you see in this image.",
            image_paths=[str(Path.cwd() / "images" / "example.jpg")]
        )
    ]
)

print(result)
```

## Best Practices

When working with Mojentic's API Layer 1, keep these best practices in mind:

1. **Choose the right model**: Different tasks require different models. Larger models generally perform better but are slower.

2. **Use structured output**: When you need specific data formats, use `generate_object()` with Pydantic models.

3. **Leverage tools**: Tools extend what LLMs can do. Use built-in tools or create custom ones for specific tasks.

4. **Manage context**: For long conversations, use ChatSession which handles context management automatically.

5. **Error handling**: Always implement proper error handling, especially when working with external LLM providers.

6. **Temperature setting**: Lower temperature (closer to 0) for more deterministic outputs, higher for more creative responses.

## Next Steps

Now that you understand the basics of Mojentic's API Layer 1, you can:

1. Explore more advanced features in the [API documentation](api_1.md)
2. Learn about Layer 2 for building agent-based systems
3. Contribute to the Mojentic project on GitHub

## Troubleshooting

Common issues and their solutions:

- **Connection errors**: Ensure your LLM provider (Ollama or OpenAI) is properly set up and accessible.
- **Model not found**: Verify that the model name is correct and available in your provider.
- **Memory issues**: Large models require significant RAM. Consider using smaller models or increasing your system's memory.
- **Slow responses**: LLM inference can be slow, especially for large models. Consider using smaller models for development.

Happy building with Mojentic!
