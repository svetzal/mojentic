# Building Chatbots with Mojentic

## Why Use Chat Sessions?

When working with Large Language Models (LLMs), simple text generation is useful for one-off interactions, but many applications require ongoing conversations where the model remembers previous exchanges. This is where chat sessions come in.

Chat sessions are essential when you need to:
- Build conversational agents or chatbots
- Maintain context across multiple user interactions
- Create applications where the LLM needs to remember previous information
- Develop more natural and coherent conversational experiences

## When to Apply This Approach

Use chat sessions when:
- Your application requires multi-turn conversations
- You need the LLM to reference information from earlier in the conversation
- You want to create a more interactive and engaging user experience
- Your use case involves complex dialogues that build on previous exchanges

## The Key Difference: Expanding Context

The fundamental difference between simple text generation and chat sessions is the **expanding context**. With each new message in a chat session:

1. The message is added to the conversation history
2. All previous messages (within token limits) are sent to the LLM with each new query
3. The LLM can reference and build upon earlier parts of the conversation
4. The conversation maintains coherence and continuity across multiple exchanges

This expanding context allows for more natural conversations and enables the LLM to provide responses that are consistent with the ongoing dialogue.

## Getting Started

Let's walk through a simple example of building a chatbot using Mojentic's ChatSession class.

### Basic Implementation

Here's the simplest way to create a chat session with Mojentic:

```python
from mojentic.llm import ChatSession, LLMBroker

# Create an LLM broker
llm_broker = LLMBroker(model="llama3.3-70b-32k")

# Initialize a chat session
chat_session = ChatSession(llm_broker)

# Simple interactive loop
while True:
    query = input("Query: ")
    if not query:
        break
    else:
        response = chat_session.send(query)
        print(response)
```

This code creates an interactive chatbot that maintains context across multiple exchanges.

## Step-by-Step Explanation

Let's break down how this example works:

### 1. Import the necessary components

```python
from mojentic.llm import ChatSession, LLMBroker
```

These imports provide:
- `ChatSession`: The class that manages the conversation state
- `LLMBroker`: The interface for interacting with LLMs

### 2. Create an LLM broker

```python
llm_broker = LLMBroker(model="llama3.3-70b-32k")
```

The `LLMBroker` is configured with a specific model. For chat applications, models with larger context windows (like the 32k variant shown here) are often beneficial as they can handle longer conversations.

### 3. Initialize a chat session

```python
chat_session = ChatSession(llm_broker)
```

The `ChatSession` is initialized with the LLM broker. By default, it:
- Sets a system prompt ("You are a helpful assistant.")
- Initializes an empty conversation history
- Sets a maximum context length (default is 32768 tokens)

### 4. Interactive conversation loop

```python
while True:
    query = input("Query: ")
    if not query:
        break
    else:
        response = chat_session.send(query)
        print(response)
```

This loop:
- Takes user input
- Sends it to the chat session
- Prints the response
- Continues until the user enters an empty query

The magic happens in the `chat_session.send(query)` method, which:
1. Adds the user's query to the conversation history
2. Sends the entire conversation history to the LLM
3. Gets the response from the LLM
4. Adds the response to the conversation history
5. Returns the response

## Customizing Your Chat Session

The `ChatSession` class offers several customization options:

```python
chat_session = ChatSession(
    llm=llm_broker,
    system_prompt="You are a helpful AI assistant specialized in technical support.",
    tools=None,  # Optional tools the LLM can use
    max_context=16384,  # Maximum context length in tokens
    temperature=0.7  # Controls randomness in responses
)
```

### System Prompt

The system prompt sets the initial context and instructions for the LLM. It's the first message in the conversation and remains constant throughout the session.

### Managing Context Length

Chat sessions automatically manage the context length to stay within the model's limits:
- New messages are added to the conversation history
- When the total token count exceeds `max_context`, older messages are removed (except the system prompt)
- This ensures the conversation can continue indefinitely without exceeding token limits

## Using Different LLM Providers

Just like with simple text generation, you can use different LLM providers with chat sessions:

```python
import os
from mojentic.llm.gateways.openai import OpenAIGateway
from mojentic.llm import ChatSession, LLMBroker

# Set up OpenAI
api_key = os.getenv("OPENAI_API_KEY")
gateway = OpenAIGateway(api_key)
llm = LLMBroker(model="gpt-4o", gateway=gateway)

# Create chat session with OpenAI
chat_session = ChatSession(llm)

# Use the chat session as before
response = chat_session.send("Hello, how can you help me today?")
print(response)
```

## Advanced Usage: Adding Tools

You can enhance your chatbot by providing tools that the LLM can use:

```python
from mojentic.llm import ChatSession, LLMBroker
from mojentic.llm.tools.date_resolver import ResolveDateTool

# Create tools
date_tool = ResolveDateTool()

# Create chat session with tools
llm_broker = LLMBroker(model="llama3.3-70b-32k")
chat_session = ChatSession(
    llm=llm_broker,
    tools=[date_tool]
)

# The LLM can now use the date tool in conversations
response = chat_session.send("What day of the week is July 4th, 2025?")
print(response)
```

## Summary

Chat sessions in Mojentic provide a powerful way to build conversational applications with LLMs. In this guide, we've learned:

1. How chat sessions differ from simple text generation through their expanding context
2. How to set up a basic chatbot using the `ChatSession` class
3. How the conversation history is maintained and managed
4. Ways to customize your chat session with system prompts and other parameters
5. How to use different LLM providers and add tools to enhance functionality

By leveraging chat sessions, you can create more engaging and coherent conversational experiences that maintain context across multiple interactions.