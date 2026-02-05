# Reasoning Effort Control

Mojentic v1.2.0 introduces `CompletionConfig` and reasoning effort control, allowing you to enable extended thinking capabilities in supported LLM models.

## CompletionConfig Overview

`CompletionConfig` is a Pydantic model that provides a unified way to configure LLM behavior:

```python
from mojentic.llm import CompletionConfig

config = CompletionConfig(
    temperature=0.7,
    num_ctx=32768,
    max_tokens=16384,
    num_predict=-1,
    reasoning_effort="high"  # Optional: low, medium, or high
)
```

### Parameters

- **temperature** (float): Controls randomness (0.0 = deterministic, 2.0 = very random). Default: 1.0
- **num_ctx** (int): Context window size in tokens. Default: 32768
- **max_tokens** (int): Maximum tokens to generate in response. Default: 16384
- **num_predict** (int): Number of tokens to predict (-1 = no limit). Default: -1
- **reasoning_effort** (str | None): Extended thinking level ("low", "medium", "high", or None). Default: None

## Using CompletionConfig with LLMBroker

Pass the config object to any broker method:

```python
from mojentic.llm import LLMBroker, CompletionConfig, LLMMessage, MessageRole
from mojentic.llm.gateways import OllamaGateway

broker = LLMBroker(model="qwen3-coder:30b", gateway=OllamaGateway())

config = CompletionConfig(
    temperature=0.3,
    reasoning_effort="high"
)

messages = [
    LLMMessage(role=MessageRole.User, content="Explain quantum entanglement")
]

response = broker.generate(messages, config=config)
print(response)
```

### Backward Compatibility

Individual kwargs are still supported but deprecated:

```python
# Old way (deprecated)
response = broker.generate(messages, temperature=0.7, num_ctx=16384)

# New way (recommended)
config = CompletionConfig(temperature=0.7, num_ctx=16384)
response = broker.generate(messages, config=config)
```

If you provide both config and individual kwargs, a `DeprecationWarning` is emitted and config takes precedence.

## Reasoning Effort Levels

The `reasoning_effort` parameter enables extended thinking in supported models:

- **None** (default): Standard response generation
- **"low"**: Quick reasoning with minimal overhead
- **"medium"**: Balanced reasoning effort
- **"high"**: Deep, thorough reasoning for complex problems

### Provider-Specific Behavior

#### Ollama Gateway

When `reasoning_effort` is set (any level), Ollama adds the `think: true` parameter to enable extended thinking:

```python
config = CompletionConfig(reasoning_effort="high")
response = broker.generate(messages, config=config)
```

The model's thinking process is captured in `response.thinking` (if available):

```python
result = broker.adapter.complete(
    model="qwen3-coder:30b",
    messages=messages,
    config=config
)

if result.thinking:
    print("Model reasoning:", result.thinking)
print("Final response:", result.content)
```

#### OpenAI Gateway

For OpenAI reasoning models (o1, o3, o4 series), the `reasoning_effort` value is passed directly to the API:

```python
from mojentic.llm.gateways import OpenAIGateway

broker = LLMBroker(model="o1-preview", gateway=OpenAIGateway())

config = CompletionConfig(reasoning_effort="medium")
response = broker.generate(messages, config=config)
```

For non-reasoning models (GPT-4, GPT-5), the parameter is ignored with a warning logged.

#### Anthropic Gateway

The Anthropic gateway does not yet support `reasoning_effort`. If provided, a warning is logged and the parameter is ignored.

## Using with ChatSession

`ChatSession` also supports `CompletionConfig`:

```python
from mojentic.llm import ChatSession, LLMBroker, CompletionConfig

broker = LLMBroker(model="qwen3-coder:30b")

config = CompletionConfig(
    temperature=0.7,
    reasoning_effort="high"
)

session = ChatSession(
    llm=broker,
    system_prompt="You are a thoughtful assistant.",
    config=config
)

response = session.send("Explain the halting problem")
print(response)
```

## Streaming with Reasoning Effort

Reasoning effort works with streaming too:

```python
config = CompletionConfig(reasoning_effort="high")

for chunk in broker.generate_stream(messages, config=config):
    print(chunk, end="", flush=True)
```

For Ollama, thinking content is streamed separately from the main response.

## Examples

### High-Stakes Reasoning Task

```python
config = CompletionConfig(
    temperature=0.1,  # Low randomness for consistency
    reasoning_effort="high"  # Deep thinking
)

messages = [
    LLMMessage(
        role=MessageRole.User,
        content="Find the bug in this sorting algorithm and explain why it fails"
    )
]

response = broker.generate(messages, config=config)
```

### Creative Generation

```python
config = CompletionConfig(
    temperature=1.5,  # High randomness for creativity
    reasoning_effort="low"  # Quick generation
)

messages = [
    LLMMessage(
        role=MessageRole.User,
        content="Write a haiku about programming"
    )
]

response = broker.generate(messages, config=config)
```

## Best Practices

1. **Use reasoning_effort="high" for**: Complex reasoning, debugging, mathematical proofs, multi-step problems
2. **Use reasoning_effort="low" or None for**: Quick responses, simple queries, creative tasks
3. **Always use CompletionConfig**: Avoid deprecated individual kwargs for cleaner, more maintainable code
4. **Provider compatibility**: Check gateway documentation for reasoning_effort support

## Migration Guide

### Before (v1.1.x)

```python
response = broker.generate(
    messages,
    temperature=0.7,
    num_ctx=32768,
    max_tokens=8192
)
```

### After (v1.2.0+)

```python
config = CompletionConfig(
    temperature=0.7,
    num_ctx=32768,
    max_tokens=8192
)

response = broker.generate(messages, config=config)
```

### Adding Reasoning Effort

```python
config = CompletionConfig(
    temperature=0.7,
    num_ctx=32768,
    max_tokens=8192,
    reasoning_effort="high"  # New!
)

response = broker.generate(messages, config=config)
```

## See Also

- [Simple Text Generation](simple_text_generation.md)
- [Chat Sessions](chat_sessions.md)
- [Tool Usage](tool_usage.md)
