# Building Chatbots with Tools with Mojentic

## Why Combine Chat Sessions with Tools?

Chat sessions provide a way to maintain context across multiple interactions, while tools extend the capabilities of Large Language Models (LLMs) beyond their training data. By combining these two powerful features, you can create chatbots that:

- Maintain conversation context across multiple exchanges
- Access real-time information and external systems
- Perform specialized calculations and operations
- Provide more accurate and helpful responses
- Solve complex problems that require both conversation memory and specialized capabilities

This combination creates intelligent assistants that can both remember your conversation history and take action when needed.

## When to Apply This Approach

Use chat sessions with tools when:

- Your application requires multi-turn conversations with specialized capabilities
- Users need to have ongoing dialogues that reference external data or systems
- You want to create assistants that can both converse naturally and perform specific tasks
- Your use case involves complex problem-solving that benefits from both memory and specialized tools

Common examples include:
- Personal assistants that can schedule appointments and answer questions about your calendar
- Customer support bots that can look up order information while maintaining conversation context
- Research assistants that can search for information and maintain the thread of an investigation
- Technical support chatbots that can diagnose problems and access documentation

## Getting Started

Let's walk through a simple example of building a chatbot with tools using Mojentic's ChatSession class.

### Basic Implementation

Here's how to create a chat session with tools:

```python
from mojentic.llm import ChatSession, LLMBroker
from mojentic.llm.tools.date_resolver import ResolveDateTool

# Create an LLM broker
llm_broker = LLMBroker(model="llama3.3-70b-32k")

# Initialize a chat session with tools
chat_session = ChatSession(
    llm=llm_broker,
    tools=[ResolveDateTool()]
)

# Simple interactive loop
while True:
    query = input("Query: ")
    if not query:
        break
    else:
        response = chat_session.send(query)
        print(response)
```

This code creates an interactive chatbot that can both maintain conversation context and resolve date-related queries.

## Step-by-Step Explanation

Let's break down how this example works:

### 1. Import the necessary components

```python
from mojentic.llm import ChatSession, LLMBroker
from mojentic.llm.tools.date_resolver import ResolveDateTool
```

These imports provide:
- `ChatSession`: The class that manages the conversation state
- `LLMBroker`: The interface for interacting with LLMs
- `ResolveDateTool`: A built-in tool for resolving date-related queries

### 2. Create an LLM broker

```python
llm_broker = LLMBroker(model="llama3.3-70b-32k")
```

The `LLMBroker` is configured with a specific model. For chat applications with tools, models with larger context windows (like the 32k variant shown here) are beneficial as they can handle longer conversations and tool interactions.

### 3. Initialize a chat session with tools

```python
chat_session = ChatSession(
    llm=llm_broker,
    tools=[ResolveDateTool()]
)
```

The key difference from a basic chat session is the addition of the `tools` parameter, which provides the chat session with access to the specified tools. In this case, we're providing the `ResolveDateTool`.

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

When the user asks a date-related question, the LLM will automatically use the `ResolveDateTool` to provide an accurate response.

## How Tool Usage Works in Chat Sessions

When a user sends a message to a chat session with tools:

1. The message is added to the conversation history
2. The entire conversation history is sent to the LLM, along with the available tools
3. The LLM determines if it needs to use any tools to respond appropriately
4. If needed, the LLM calls the relevant tool(s) and receives the results
5. The LLM incorporates the tool results into its response
6. The response is added to the conversation history
7. The cycle continues with each new user message

This process happens automatically, with the LLM deciding when and how to use the available tools based on the conversation context.

## Example Conversation

Here's an example of what a conversation might look like with a chat session that has access to the `ResolveDateTool`:

```
User: Hello, can you help me with some date calculations?
AI: Hello! I'd be happy to help you with date calculations. What would you like to know?

User: What day of the week is July 4th, 2025?
AI: July 4th, 2025 falls on a Friday.

User: How many days are there between today and Christmas?
AI: Today is [current date], and Christmas is on December 25th. There are [calculated number] days between today and Christmas.

User: And what day will it be 90 days from now?
AI: 90 days from today ([current date]) will be [calculated date], which is a [day of week].
```

Notice how the chatbot maintains the conversation context while also providing accurate date calculations using the tool.

## Using Multiple Tools

You can provide multiple tools to a chat session, and the LLM will choose the appropriate one based on the conversation:

```python
from mojentic.llm import ChatSession, LLMBroker
from mojentic.llm.tools.date_resolver import ResolveDateTool
from mytools.calculator import CalculatorTool
from mytools.weather import WeatherTool

# Create an LLM broker
llm_broker = LLMBroker(model="qwq")

# Initialize a chat session with multiple tools
chat_session = ChatSession(
    llm=llm_broker,
    tools=[
        ResolveDateTool(),
        CalculatorTool(),
        WeatherTool(api_key="your_api_key")
    ]
)

# Use the chat session as before
response = chat_session.send("What's the weather like in New York today, and what day of the week is it?")
print(response)
```

In this example, the LLM might use both the `WeatherTool` and the `ResolveDateTool` to provide a comprehensive response.

## Creating Custom Tools for Chat Sessions

You can create custom tools for your chat sessions following the same pattern described in the [Building Tools](building_tools.md) guide. Any tool that works with the `LLMBroker.generate()` method will also work with chat sessions.

Here's a simple example of creating and using a custom tool in a chat session:

```python
from mojentic.llm import ChatSession, LLMBroker
from mojentic.llm.tools.llm_tool import LLMTool

class CurrentDateTimeTool(LLMTool):
    def run(self, format_string: str = "%Y-%m-%d %H:%M:%S") -> dict:
        """Returns the current date and time."""
        from datetime import datetime
        current_time = datetime.now()
        formatted_time = current_time.strftime(format_string)

        return {
            "current_datetime": formatted_time,
            "timestamp": current_time.timestamp(),
            "timezone": datetime.now().astimezone().tzname()
        }

    @property
    def descriptor(self):
        return {
            "type": "function",
            "function": {
                "name": "get_current_datetime",
                "description": "Get the current date and time. Useful when you need to know the current time or date.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "format_string": {
                            "type": "string",
                            "description": "Format string for the datetime using Python's strftime() directives."
                        }
                    },
                    "required": []
                }
            }
        }

# Create an LLM broker
llm_broker = LLMBroker(model="llama3.3-70b-32k")

# Initialize a chat session with the custom tool
chat_session = ChatSession(
    llm=llm_broker,
    tools=[CurrentDateTimeTool()]
)

# Use the chat session
response = chat_session.send("What time is it right now?")
print(response)
```

## Advanced Usage: Stateful Tools in Chat Sessions

Some tools might need to maintain state across multiple interactions within a chat session. For example, a database tool might need to maintain a connection, or a game tool might need to track the game state.

Here's an example of a stateful tool that maintains a simple counter:

```python
from mojentic.llm import ChatSession, LLMBroker
from mojentic.llm.tools.llm_tool import LLMTool

class CounterTool(LLMTool):
    def __init__(self):
        self.count = 0

    def run(self, action: str = "increment") -> dict:
        """Manages a simple counter."""
        if action.lower() == "increment":
            self.count += 1
        elif action.lower() == "decrement":
            self.count -= 1
        elif action.lower() == "reset":
            self.count = 0

        return {
            "count": self.count,
            "action_performed": action
        }

    @property
    def descriptor(self):
        return {
            "type": "function",
            "function": {
                "name": "manage_counter",
                "description": "Manages a simple counter that persists across the conversation.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "action": {
                            "type": "string",
                            "enum": ["increment", "decrement", "reset"],
                            "description": "The action to perform on the counter."
                        }
                    },
                    "required": []
                }
            }
        }

# Create a chat session with the stateful tool
llm_broker = LLMBroker(model="llama3.3-70b-32k")
counter_tool = CounterTool()
chat_session = ChatSession(
    llm=llm_broker,
    tools=[counter_tool]
)

# The counter will maintain its state across multiple interactions
```

## Best Practices for Chat Sessions with Tools

When building chatbots with tools, follow these best practices:

### 1. Choose the Right Tools

- **Relevant tools**: Only include tools that are relevant to the chatbot's purpose
- **Complementary capabilities**: Choose tools that complement each other and the LLM's capabilities
- **Clear boundaries**: Each tool should have a clear and distinct purpose

### 2. Provide Clear System Prompts

- **Set expectations**: Use the system prompt to tell the LLM when and how to use tools
- **Define the chatbot's role**: Clearly state what the chatbot should and shouldn't do
- **Guide tool usage**: Provide guidelines for when the LLM should use tools vs. its own knowledge

Example system prompt:
```
You are a helpful assistant with access to tools for date calculations, weather information, and simple math. 
Use these tools when you need precise information that you might not have or when calculations are required. 
For general knowledge questions, use your training data instead of tools.
```

### 3. Handle Tool Failures Gracefully

- **Error handling**: Ensure your tools have robust error handling
- **Fallback responses**: Provide fallback options when tools fail
- **Transparent communication**: Be clear with users when a tool fails and why

### 4. Balance Tool Usage with Conversation Flow

- **Natural integration**: Tool usage should feel like a natural part of the conversation
- **Avoid over-reliance**: Don't use tools when the LLM's knowledge is sufficient
- **Maintain context**: Ensure tool usage doesn't disrupt the conversation flow

## Summary

Chat sessions with tools in Mojentic provide a powerful way to build intelligent assistants that combine conversation memory with specialized capabilities. In this guide, we've learned:

1. How to create a chat session with tools using the `ChatSession` class
2. How tool usage works within the context of a conversation
3. How to use multiple tools in a chat session
4. How to create custom tools for chat sessions
5. Best practices for building effective chatbots with tools

By combining chat sessions with tools, you can create more capable, accurate, and helpful AI assistants that maintain conversation context while also performing specialized tasks and accessing external information.
