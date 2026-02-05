# Streaming Responses

Mojentic supports streaming responses from LLMs, providing a better user experience by showing content as it arrives rather than waiting for the complete response. Streaming works seamlessly with tool calling, allowing you to stream content before, during, and after tool execution.

## Overview

The `LLMBroker.generate_stream()` method mirrors the `generate()` method but yields content chunks as they arrive from the LLM. This is particularly useful for:

- Long-form content generation (stories, articles, explanations)
- Interactive chat applications where users want immediate feedback
- Agentic workflows where tools are called and you want to show progress
- Any scenario where reducing perceived latency improves UX

## Supported Gateways

| Gateway | Streaming Support | Tool Support | Notes |
|---------|------------------|--------------|-------|
| **OllamaGateway** | ✅ Full | ✅ Full | Tool calls arrive complete |
| **OpenAIGateway** | ✅ Full | ✅ Full | Handles incremental tool arguments |
| **AnthropicGateway** | ❌ Not yet | ❌ N/A | Coming soon |

## Basic Usage

### Simple Text Streaming

```python
from mojentic.llm import LLMBroker
from mojentic.llm.gateways import OllamaGateway
from mojentic.llm.gateways.models import LLMMessage

broker = LLMBroker(
    model="qwen2.5:7b",
    gateway=OllamaGateway()
)

# Stream the response
stream = broker.generate_stream(
    messages=[LLMMessage(content="Tell me a short story about a dragon")],
    temperature=0.7
)

# Print chunks as they arrive
for chunk in stream:
    print(chunk, end='', flush=True)

print("\nDone!")
```

### Streaming with OpenAI

```python
import os
from mojentic.llm import LLMBroker
from mojentic.llm.gateways import OpenAIGateway
from mojentic.llm.gateways.models import LLMMessage

broker = LLMBroker(
    model="gpt-4o-mini",
    gateway=OpenAIGateway(api_key=os.getenv("OPENAI_API_KEY"))
)

stream = broker.generate_stream(
    messages=[LLMMessage(content="Count to 10, one number per line")],
    temperature=0.7
)

for chunk in stream:
    print(chunk, end='', flush=True)
```

## Streaming with Tool Calling

One of the most powerful features is that streaming works seamlessly with tool calling. The broker automatically:

1. Streams content as it arrives
2. Detects when tool calls are made
3. Executes the tools
4. Recursively streams the response after tool execution

### Example with Date Resolution

```python
from mojentic.llm import LLMBroker
from mojentic.llm.gateways import OpenAIGateway
from mojentic.llm.gateways.models import LLMMessage
from mojentic.llm.tools.date_resolver import ResolveDateTool
import os

broker = LLMBroker(
    model="gpt-4o-mini",
    gateway=OpenAIGateway(api_key=os.getenv("OPENAI_API_KEY"))
)

date_tool = ResolveDateTool()

# This will:
# 1. Stream any initial content
# 2. Call the date tool when needed
# 3. Stream the response after tool execution
stream = broker.generate_stream(
    messages=[
        LLMMessage(content="Tell me a story about tomorrow and next week")
    ],
    tools=[date_tool],
    temperature=0.7
)

for chunk in stream:
    print(chunk, end='', flush=True)
```

### Content Before Tool Calls

Modern LLMs are optimized to call tools directly without extra explanation. If you want to see the LLM's reasoning before it calls tools, explicitly ask for it:

```python
stream = broker.generate_stream(
    messages=[
        LLMMessage(content="What is the date tomorrow? "
                          "First, explain what you're going to do, "
                          "then call the tool.")
    ],
    tools=[date_tool]
)

# Output will be like:
# "I will use the date resolution tool to find tomorrow's date..."
# [tool call happens]
# "Tomorrow is November 13, 2025."
```

## How It Works

### For Ollama

1. Content chunks arrive and are yielded immediately
2. Tool calls arrive complete in the stream
3. When a tool call is detected, it's executed
4. The broker recursively calls `generate_stream()` with the tool result
5. The response after tool execution is also streamed

### For OpenAI

The OpenAI implementation is more complex because tool arguments arrive incrementally:

1. Content chunks arrive and are yielded immediately
2. Tool call chunks arrive piece-by-piece:
   - First chunk: `id`, `name`, empty `arguments`
   - Subsequent chunks: fragments of `arguments` JSON
3. Tool arguments are accumulated until `finish_reason == 'tool_calls'`
4. Complete tool calls are parsed and executed
5. Recursive streaming continues with tool results

Example of OpenAI tool call streaming:
```
Chunk 1: id='call_123', name='get_weather', arguments=''
Chunk 2: arguments='{"'
Chunk 3: arguments='location'
Chunk 4: arguments='":"'
Chunk 5: arguments='San'
Chunk 6: arguments=' Francisco'
Chunk 7: arguments='"}'
Finish: tool_calls
```

## Method Signature

```python
def generate_stream(
    self,
    messages: List[LLMMessage],
    tools=None,
    config: Optional[CompletionConfig] = None,
    temperature=None,
    num_ctx=None,
    num_predict=None,
    max_tokens=None,
    correlation_id: str = None
) -> Iterator[str]:
    """
    Generate a streaming text response from the LLM.

    Yields content chunks as they arrive. When tool calls are detected,
    executes them and recursively streams the response.

    Parameters
    ----------
    messages : List[LLMMessage]
        A list of messages to send to the LLM.
    tools : List[Tool]
        A list of tools to use with the LLM.
    config : CompletionConfig, optional
        Configuration object controlling generation behavior (preferred).
    temperature : float, optional
        (Legacy) The temperature to use for the response.
    num_ctx : int, optional
        (Legacy) The number of context tokens to use.
    num_predict : int, optional
        (Legacy) The number of tokens to predict.
    max_tokens : int, optional
        (Legacy) The maximum number of tokens to generate.
    correlation_id : str
        UUID string for tracing events.

    Note
    ----
    Prefer using `config=CompletionConfig(...)` over individual kwargs.
    If both are provided, config takes precedence.

    Yields
    ------
    str
        Content chunks as they arrive from the LLM.
    """
```

## Best Practices

### 1. Always Flush Output

When printing streaming content, use `flush=True` to ensure immediate display:

```python
for chunk in stream:
    print(chunk, end='', flush=True)
```

### 2. Handle Exceptions

Wrap streaming in try/except to handle network errors gracefully:

```python
try:
    for chunk in broker.generate_stream(messages=messages, tools=tools):
        print(chunk, end='', flush=True)
except Exception as e:
    print(f"\nError during streaming: {e}")
```

### 3. Use with Tracer for Debugging

The tracer system records all streaming activity:

```python
from mojentic.tracer import TracerSystem

tracer = TracerSystem()
broker = LLMBroker(
    model="gpt-4o-mini",
    gateway=OpenAIGateway(),
    tracer=tracer
)

# Stream with full observability
stream = broker.generate_stream(messages=messages, tools=tools)
for chunk in stream:
    print(chunk, end='', flush=True)

# Review what happened
events = tracer.get_events()
```

### 4. Check Gateway Support

Not all gateways support streaming. Check before use:

```python
if hasattr(broker.adapter, 'complete_stream'):
    stream = broker.generate_stream(messages=messages)
else:
    response = broker.generate(messages=messages)
```

## Limitations

### Structured Output

Streaming does not work with structured output (`generate_object()`). This is an API limitation from OpenAI:

```python
# This will raise NotImplementedError
stream = broker.generate_stream(
    messages=messages,
    object_model=MyPydanticModel  # ❌ Not supported
)

# Use non-streaming for structured output
obj = broker.generate_object(
    messages=messages,
    object_model=MyPydanticModel  # ✅ Works
)
```

### Model Compatibility

OpenAI's streaming respects model capabilities. Reasoning models and some older models may not support streaming:

```python
# The gateway will raise NotImplementedError if model doesn't support streaming
try:
    stream = broker.generate_stream(
        messages=messages,
        model="o1-preview"  # May not support streaming
    )
except NotImplementedError as e:
    print(f"Model doesn't support streaming: {e}")
```

## Performance Considerations

### Latency vs. Throughput

- **Streaming**: Lower perceived latency, better UX, same total time
- **Non-streaming**: Higher perceived latency, worse UX, same total time

Streaming doesn't make responses faster—it shows them sooner.

### Tool Call Overhead

Each tool call in streaming mode:
1. Waits for complete tool arguments (OpenAI)
2. Executes the tool synchronously
3. Makes a new streaming request

For workflows with many tool calls, this adds network round-trips.

### Memory Usage

Streaming uses less memory than buffering full responses, especially for long-form content.

## Examples

See the complete working example at `src/_examples/streaming.py` in the repository.

## API Reference

For detailed API documentation, see:

- [LLMBroker.generate_stream()][mojentic.llm.LLMBroker.generate_stream]
- [OllamaGateway.complete_stream()][mojentic.llm.gateways.OllamaGateway.complete_stream]
- [OpenAIGateway.complete_stream()][mojentic.llm.gateways.OpenAIGateway.complete_stream]
