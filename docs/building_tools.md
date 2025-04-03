# Building Tools for LLMs in Mojentic

## Introduction to LLM Tools

Tools are a powerful way to extend the capabilities of Large Language Models (LLMs). While LLMs excel at generating text based on patterns they've learned during training, they have inherent limitations:

- They don't have access to real-time information
- They can't perform precise calculations or execute code
- They lack the ability to interact with external systems
- Their knowledge is limited to their training data

By creating custom tools, you can overcome these limitations and build more powerful, accurate, and useful AI applications.

## Why Build Custom Tools?

Custom tools allow you to:

1. **Extend LLM capabilities**: Give your LLM abilities beyond text generation
2. **Improve accuracy**: Provide precise, up-to-date information
3. **Add domain-specific functionality**: Create specialized tools for your particular use case
4. **Integrate with existing systems**: Connect your LLM to databases, APIs, or other services
5. **Reduce hallucinations**: Give the LLM factual data rather than relying on its internal knowledge

## Building Your First Tool: Current Date and Time

Let's create a simple tool that returns the current date and time. This is a great first example because:

- It's straightforward to implement
- It provides information the LLM doesn't inherently have (current time)
- It demonstrates the basic structure of a Mojentic tool

Here's how to build a CurrentDateTimeTool:

```python
from datetime import datetime
from mojentic.llm.tools.llm_tool import LLMTool

class CurrentDateTimeTool(LLMTool):
    def run(self, format_string: str = "%Y-%m-%d %H:%M:%S") -> dict:
        """
        Returns the current date and time.

        Parameters
        ----------
        format_string : str, optional
            The format string for the datetime, by default "%Y-%m-%d %H:%M:%S"

            Format specifiers follow Python's datetime strftime() directives:
            - %Y: 4-digit year (e.g., 2023)
            - %m: Month as a zero-padded decimal (01-12)
            - %d: Day of the month as a zero-padded decimal (01-31)
            - %H: Hour (24-hour clock) as a zero-padded decimal (00-23)
            - %M: Minute as a zero-padded decimal (00-59)
            - %S: Second as a zero-padded decimal (00-59)
            - %A: Full weekday name (e.g., Monday)
            - %B: Full month name (e.g., January)
            - %I: Hour (12-hour clock) as a zero-padded decimal (01-12)
            - %p: AM/PM

            Examples:
            - "%Y-%m-%d" → "2023-11-28"
            - "%A, %B %d, %Y" → "Tuesday, November 28, 2023"
            - "%I:%M %p" → "02:30 PM"

            For a complete reference, see Python's datetime formatting documentation:
            https://docs.python.org/3/library/datetime.html#strftime-and-strptime-format-codes

        Returns
        -------
        dict
            A dictionary containing the current date and time
        """
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
                            "description": """Format string for the datetime using Python's strftime() directives.

Common specifiers:
- %Y: 4-digit year (e.g., 2023)
- %m: Month as a zero-padded decimal (01-12)
- %d: Day of the month as a zero-padded decimal (01-31)
- %H: Hour (24-hour clock) as a zero-padded decimal (00-23)
- %M: Minute as a zero-padded decimal (00-59)
- %S: Second as a zero-padded decimal (00-59)
- %A: Full weekday name (e.g., Monday)
- %B: Full month name (e.g., January)
- %I: Hour (12-hour clock) as a zero-padded decimal (01-12)
- %p: AM/PM

Examples:
- '%Y-%m-%d' → '2023-11-28'
- '%A, %B %d, %Y' → 'Tuesday, November 28, 2023'
- '%I:%M %p' → '02:30 PM'

Default is '%Y-%m-%d %H:%M:%S'.
"""
                        }
                    },
                    "required": []
                }
            }
        }
```

## Understanding the Tool Structure

Every tool in Mojentic must implement two key components:

1. **The `run` method**: This contains the actual functionality of your tool
2. **The `descriptor` property**: This describes your tool's capabilities so the LLM knows when to request it

### The `run` Method

The `run` method is where you implement the actual functionality of your tool. It should:

- Accept parameters that the LLM will provide
- Perform the necessary operations
- Return the results in a structured format (typically a dictionary)

In our example, the `run` method:
- Takes an optional `format_string` parameter
- Gets the current date and time
- Formats it according to the provided format string
- Returns a dictionary with the formatted time, timestamp, and timezone

### The `descriptor` Property

The `descriptor` property is crucial - it communicates your tool's capabilities so the LLM can determine when to request it. This property returns a dictionary that follows the OpenAI function calling format, containing:

- **name**: A unique identifier for your tool
- **description**: A clear explanation of what your tool does
- **parameters**: The inputs your tool accepts, including:
  - Types (string, number, boolean, etc.)
  - Descriptions
  - Whether they're required or optional

The descriptor is essentially the "API documentation" that helps the LLM understand:
- When and why to request your tool
- What parameters to include in the request
- What to expect in return

When the LLM makes a tool request, the LLMBroker detects it, calls the appropriate tool, and passes the results back to the LLM.

## Using Your Custom Tool

Now that we've built our tool, let's see how to use it:

```python
from mojentic.llm.gateways.models import LLMMessage
from mojentic.llm.llm_broker import LLMBroker
from mojentic.llm.tools.current_datetime import CurrentDateTimeTool

# Create an LLM broker
llm = LLMBroker(model="llama3")

# Create our custom tool
datetime_tool = CurrentDateTimeTool()

# Generate a response with tool assistance
result = llm.generate(
    messages=[LLMMessage(content="What time is it right now? Also, what day of the week is it today?")],
    tools=[datetime_tool]
)

print(result)
```

When the LLM receives a query about the current time or date, the following happens:
1. The LLM recognizes that it needs current time information
2. The LLM requests that the `CurrentDateTimeTool` be called
3. The LLMBroker detects this request and calls the tool
4. The LLMBroker passes the tool's result back to the LLM
5. The LLM incorporates this information into its response

## Best Practices for Tool Design

When creating tools for LLMs, follow these best practices:

### 1. Clear Descriptors

The descriptor is how the LLM understands your tool. Make it clear and comprehensive:

- **Descriptive names**: Use names that clearly indicate what the tool does
- **Detailed descriptions**: Explain when and why to use the tool, imagine it has a hundred tools to choose from, when should it use this one?
- **Parameter documentation**: Clearly describe each parameter and its purpose

### 2. Robust Implementation

Your tool should be reliable and handle edge cases:

- **Input validation**: Check that inputs are valid before processing
- **Error handling**: Return helpful error messages when something goes wrong
- **Default values**: Provide sensible defaults for optional parameters

### 3. Focused Functionality

Each tool should do one thing well:

- **Single responsibility**: Each tool should have a clear, specific purpose
- **Composability**: Create multiple simple tools rather than one complex tool
- **Reusability**: Design tools that can be used in multiple contexts

## Advanced Tool Concepts

As you become more comfortable with building basic tools, you can explore more advanced concepts:

### Stateful Tools

Some tools might need to maintain state between calls. For example, a database tool might need to maintain a connection:

```python
class DatabaseQueryTool(LLMTool):
    def __init__(self, connection_string):
        self.connection = self._establish_connection(connection_string)

    def run(self, query):
        # Execute query using self.connection
        pass
```

### Tools with LLM Dependencies

Some tools might need to use the LLM themselves:

```python
class TextSummarizerTool(LLMTool):
    def __init__(self, llm_broker):
        self.llm = llm_broker

    def run(self, text):
        # Use the LLM to summarize the text
        summary = self.llm.generate(messages=[LLMMessage(content=f"Summarize this text: {text}")])
        return {"summary": summary}
```

Imagine you are using tools in a chat session leveraging a general-purpose LLM like `qwq`, but you want to provide a tool that can write code like `qwen2.5-coder` - this can give you the best of both worlds in your application.

## Conclusion

Building custom tools is a powerful way to extend the capabilities of LLMs in your applications. By following the patterns and practices outlined in this guide, you can create tools that:

- Provide real-time information
- Perform specialized calculations
- Integrate with external systems
- Add domain-specific functionality

Remember that the key to effective tool design is clear communication with the LLM through well-designed descriptors, and robust implementation through carefully crafted `run` methods.

In the next guide, [Tool Usage](tool_usage.md), we'll explore more examples of how to use tools with LLMs in Mojentic.
