# Simple Text Generation with Mojentic

## Why Use Simple Text Generation?

When working with Large Language Models (LLMs), the most basic operation is generating text responses to prompts. This fundamental capability forms the foundation for more complex interactions and is essential for any application that requires natural language processing.

Simple text generation is useful when you need to:

- Get quick answers or explanations from an LLM
- Generate creative content like stories or descriptions
- Obtain information or assistance on various topics
- Test the basic functionality of your LLM integration

## When to Apply This Approach

Use simple text generation when:

- You need straightforward text responses without structured data
- You're just getting started with Mojentic and want to test basic functionality
- Your use case doesn't require complex tools or structured outputs
- You want to explore the capabilities of different LLM models

## Getting Started

Let's walk through a simple example of text generation using Mojentic. We'll start with the most basic implementation and then explore how it works.

### Basic Implementation

Here's the simplest way to generate text with Mojentic:

```python
from mojentic.llm.gateways.models import LLMMessage
from mojentic.llm.llm_broker import LLMBroker

# Create an LLM broker (model parameter is required)
llm = LLMBroker(model="qwen2.5:14b")

# Generate a response to a simple prompt
result = llm.generate(messages=[LLMMessage(content='Hello, how are you?')])
print(result)
```

This code will connect to an LLM (using Ollama by default) and generate a response to the greeting.

## Step-by-Step Explanation

Let's break down how this example works:

### 1. Import the necessary components

```python
from mojentic.llm.gateways.models import LLMMessage
from mojentic.llm.llm_broker import LLMBroker
```

These imports provide:
- `LLMMessage`: A class for creating messages to send to the LLM
- `LLMBroker`: The main interface for interacting with LLMs

### 2. Create an LLM broker

```python
llm = LLMBroker(model="llama3")
```

The `LLMBroker` is the central component that manages communication with the LLM:
- The `model` parameter is required and specifies which model to use (e.g., "llama3")
- By default, it uses the Ollama gateway to connect to locally running models (if no gateway is specified)

### 3. Generate text

```python
result = llm.generate(messages=[LLMMessage(content='Hello, how are you?')])
```

The `generate` method:
- Takes a list of `LLMMessage` objects (even if there's just one message)
- Sends them to the LLM
- Returns the generated text response

### 4. Display the result

```python
print(result)
```

The result is a string containing the LLM's response to your prompt.

## Using Different LLM Providers

Mojentic supports multiple LLM providers. Here's how to use OpenAI models:

```python
import os
from mojentic.llm.gateways.openai import OpenAIGateway
from mojentic.llm.llm_broker import LLMBroker
from mojentic.llm.gateways.models import LLMMessage

# Set up OpenAI
api_key = os.getenv("OPENAI_API_KEY")
gateway = OpenAIGateway(api_key)
llm = LLMBroker(model="gpt-4o", gateway=gateway)

# Generate text
result = llm.generate(messages=[LLMMessage(content='Hello, how are you?')])
print(result)
```

## Summary

Simple text generation is the most basic way to interact with LLMs through Mojentic. In this example, we've learned:

1. How to set up an `LLMBroker` to communicate with an LLM
2. How to create and send messages to generate text responses
3. How to use different LLM providers (Ollama and OpenAI)

This foundation serves as the building block for more advanced features like structured output generation, tool usage, and image analysis, which we'll explore in other examples.

By mastering simple text generation, you've taken the first step toward leveraging the full power of LLMs in your applications with Mojentic.
