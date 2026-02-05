# OpenAI Gateway Infrastructure

## Overview

This document describes the model registry system implemented for the OpenAI gateway. The registry provides centralized management of OpenAI model capabilities, parameter requirements, and API endpoint support, enabling automatic parameter adaptation and compatibility handling across OpenAI's diverse model catalog.

## Problem Statement

OpenAI models vary significantly in their parameter requirements and capabilities:
- **Reasoning models** (o1, o3, o4, gpt-5 series): Use `max_completion_tokens` instead of `max_tokens`
- **Chat models** (GPT-4, GPT-3.5 series): Use `max_tokens`
- **Legacy models** (babbage-002, davinci-002, gpt-3.5-turbo-instruct): Use completions endpoint instead of chat
- **Specialized models**: Some support only specific API endpoints or temperature values

Users were getting errors like:
```
openai.BadRequestError: Error code: 400 - {'error': {'message': "Unsupported parameter: 'max_tokens' is not supported with this model. Use 'max_completion_tokens' instead."}}
```

## Solution Architecture

### 1. Model Registry System (`openai_model_registry.py`)

**Core Components:**
- `ModelType` enum: Classifies models (REASONING, CHAT, EMBEDDING, MODERATION)
- `ModelCapabilities` dataclass: Defines model-specific capabilities and parameter requirements
- `OpenAIModelRegistry` class: Manages model configurations and provides lookup functionality

**Features:**
- ✅ Pre-populated with 100+ known OpenAI models
- ✅ Pattern matching for unknown models
- ✅ Runtime registration of new models and patterns
- ✅ Automatic parameter name resolution (`get_token_limit_param()`)
- ✅ Temperature validation and API endpoint awareness

### 2. Enhanced OpenAI Gateway (`openai.py`)

**Key Improvements:**
- ✅ Registry-based model detection (replaces hardcoded patterns)
- ✅ Automatic parameter adaptation (`max_tokens` ↔ `max_completion_tokens`)
- ✅ Enhanced logging for debugging parameter issues
- ✅ Parameter validation with helpful error messages
- ✅ Better error handling for API parameter mismatches

**New Methods:**
- `_validate_model_parameters()`: Pre-flight parameter validation
- `_adapt_parameters_for_model()`: Registry-based parameter adaptation
- `_is_reasoning_model()`: Simplified using registry

### 3. Comprehensive Testing

**Test Coverage:**
- ✅ Model registry functionality (`openai_model_registry_spec.py`)
- ✅ Parameter adaptation logic (updated `openai_gateway_spec.py`)
- ✅ Unknown model handling
- ✅ Registry extensibility

## ModelCapabilities Fields

The `ModelCapabilities` dataclass defines all model-specific properties:

**Type and Core Support:**
- `model_type`: ModelType enum (REASONING, CHAT, EMBEDDING, MODERATION)
- `supports_tools`: bool — Whether the model supports function/tool calling
- `supports_streaming`: bool — Whether the model supports streaming responses
- `supports_vision`: bool — Whether the model supports image inputs

**Token Limits:**
- `max_context_tokens`: Optional[int] — Maximum input context window
- `max_output_tokens`: Optional[int] — Maximum output tokens

**Temperature Support:**
- `supported_temperatures`: Optional[List[float]] — Temperature restrictions
  - `None` = All temperature values supported (default)
  - `[]` = Temperature parameter not allowed
  - `[1.0]` = Only temperature=1.0 supported

**API Endpoint Support (v1.1.0):**
- `supports_chat_api`: bool — Supports `/v1/chat/completions` endpoint (default: True)
- `supports_completions_api`: bool — Supports `/v1/completions` endpoint (default: False)
- `supports_responses_api`: bool — Supports `/v1/responses` endpoint (default: False)

## API Endpoint Support

OpenAI provides three main API endpoints with different model compatibility:

### Chat API (`/v1/chat/completions`)
**Most common endpoint** — Supports conversational message format with roles (user, assistant, system, tool).
- **Models**: Most GPT-4, GPT-4.1, GPT-4o, GPT-3.5-turbo, o1, o3, o4, gpt-5 models
- **Features**: Tool calling, streaming, multi-turn conversations
- **Example**: `gpt-4o`, `o1`, `gpt-5`

### Completions API (`/v1/completions`)
**Legacy endpoint** — Simple prompt-completion interface without message structure.
- **Models**: babbage-002, davinci-002, gpt-3.5-turbo-instruct, some newer dual-endpoint models
- **Features**: Direct text completion, no tool calling
- **Example**: `gpt-3.5-turbo-instruct`, `babbage-002`

### Responses API (`/v1/responses`)
**Newer endpoint** — Specialized for advanced reasoning and research tasks.
- **Models**: o1-pro, o3-deep-research, o4-mini-deep-research, gpt-5-pro, codex-mini-latest
- **Features**: Extended reasoning, longer output, research-oriented
- **Example**: `gpt-5-pro`, `o3-deep-research`

### Dual-Endpoint Models
Some models support multiple endpoints:
- `gpt-4o-mini`: Chat + Completions
- `gpt-4.1-nano`: Chat + Completions
- `gpt-5.1`: Chat + Completions

**Note**: The Mojentic gateway currently only uses the Chat API. The endpoint support flags are informational and used for future compatibility planning.

## Model Classification

### Reasoning Models
**Pattern**: o1*, o3*, o4*, gpt-5*
**Parameter**: `max_completion_tokens`
**Tools/Streaming**: Most now support both (as of 2026-02-04 audit)
**Exceptions**:
- `gpt-5-pro`: Responses API only, no tools/streaming
- `o3-deep-research`, `o4-mini-deep-research`: Responses API, support tools/streaming
- Audio/search variants: Limited tool/streaming support

**Examples**:
```python
# o1, o3, o4 series
o1, o1-2024-12-17, o1-pro
o3, o3-mini, o3-pro, o3-deep-research
o4-mini, o4-mini-deep-research

# GPT-5 series
gpt-5, gpt-5-mini, gpt-5-nano, gpt-5-pro
gpt-5.1, gpt-5.1-2025-11-13, gpt-5.1-chat-latest
gpt-5.2, gpt-5.2-2025-12-11, gpt-5.2-chat-latest
gpt-5-codex, codex-mini-latest
```

### Chat Models
**Pattern**: gpt-4*, gpt-4.1*, gpt-3.5*
**Parameter**: `max_tokens`
**Tools/Streaming**: Generally supported
**Exceptions**:
- Audio models (`gpt-4o-audio-preview`): No tools/streaming
- Search models (`gpt-4o-search-preview`): No tools, no temperature parameter
- `chatgpt-4o-latest`: No tools
- `gpt-4.1-nano`: No tools
- Instruct models (`gpt-3.5-turbo-instruct`): Completions API only

**Examples**:
```python
# GPT-4 series
gpt-4, gpt-4-turbo, gpt-4o, gpt-4o-mini
chatgpt-4o-latest

# GPT-4.1 series
gpt-4.1, gpt-4.1-mini, gpt-4.1-nano

# GPT-3.5 series
gpt-3.5-turbo, gpt-3.5-turbo-0125
gpt-3.5-turbo-instruct  # Completions API

# Special variants
gpt-4o-audio-preview
gpt-4o-search-preview
gpt-5-chat-latest       # Chat model, not reasoning
gpt-5-search-api
```

### Embedding Models
**Pattern**: text-embedding*
**Endpoint**: Embeddings API (`/v1/embeddings`)
**Examples**: `text-embedding-3-large`, `text-embedding-3-small`, `text-embedding-ada-002`

### Legacy Models
**Completions API only** — No chat, tools, or streaming support.
**Examples**: `babbage-002`, `davinci-002`

### Unknown Models
**Fallback**: Pattern matching infers type based on name
**Logging**: Pattern matching attempts logged for debugging
**Default**: Chat model capabilities if no pattern matches

## Temperature Restrictions

Different models have varying temperature support:

**All temperatures supported** (`supported_temperatures=None`):
- Most chat models (gpt-4, gpt-4o, gpt-3.5-turbo)
- gpt-5.1 base models (gpt-5.1, gpt-5.1-2025-11-13)
- gpt-5.2 base models (gpt-5.2, gpt-5.2-2025-12-11)

**Only temperature=1.0** (`supported_temperatures=[1.0]`):
- Most reasoning models (o1, o3, o4)
- Most gpt-5 models
- Chat-latest variants (gpt-5.1-chat-latest, gpt-5.2-chat-latest)
- Codex models

**No temperature parameter** (`supported_temperatures=[]`):
- Search models (gpt-4o-search-preview, gpt-5-search-api)

Check temperature support programmatically:
```python
caps = registry.get_model_capabilities("gpt-5")
if caps.supports_temperature(0.7):
    # Use temperature=0.7
else:
    # Use default or no temperature
```

## Key Benefits

### 1. Automatic Parameter Handling
```python
# Before: Manual parameter management required
# After: Automatic adaptation based on model type
gateway.complete(
    model="o1",  # Reasoning model
    messages=messages,
    max_tokens=1000   # Automatically converted to max_completion_tokens
)
```

### 2. Enhanced Debugging
```
INFO: Converted token limit parameter for model
  model=o1
  from_param=max_tokens
  to_param=max_completion_tokens
  value=1000
```

### 3. Endpoint Awareness
```python
from mojentic.llm.gateways.openai_model_registry import get_model_registry

registry = get_model_registry()

# Check endpoint support
caps = registry.get_model_capabilities("gpt-4o-mini")
print(caps.supports_chat_api)        # True
print(caps.supports_completions_api) # True  (dual-endpoint model)

# Check a responses-only model
caps = registry.get_model_capabilities("gpt-5-pro")
print(caps.supports_chat_api)        # False
print(caps.supports_responses_api)   # True
```

### 4. Extensible Architecture
```python
# Easy to add new models
from mojentic.llm.gateways.openai_model_registry import (
    get_model_registry, ModelCapabilities, ModelType
)

registry = get_model_registry()
registry.register_model("custom-model-v1", ModelCapabilities(
    model_type=ModelType.REASONING,
    supports_tools=True,
    supports_streaming=True,
    max_output_tokens=50000
))

# Easy to add new patterns
registry.register_pattern("custom", ModelType.CHAT)
```

### 5. Better Error Messages
```
ValueError: Reasoning model 'o1' requires 'max_completion_tokens' instead of 'max_tokens'. This should be handled automatically by parameter adaptation.
```

## Usage Examples

### Basic Usage (Automatic)
```python
from mojentic.llm.gateways.openai import OpenAIGateway

gateway = OpenAIGateway(api_key="your-key")

# Works automatically for both model types
response = gateway.complete(
    model="o1",  # or "gpt-4o"
    messages=messages,
    max_tokens=1000   # Automatically adapted as needed
)
```

### Querying Model Capabilities
```python
from mojentic.llm.gateways.openai_model_registry import get_model_registry

registry = get_model_registry()

# Get capabilities for a specific model
caps = registry.get_model_capabilities("gpt-4o")
print(f"Supports tools: {caps.supports_tools}")
print(f"Supports streaming: {caps.supports_streaming}")
print(f"Supports vision: {caps.supports_vision}")
print(f"Max context: {caps.max_context_tokens}")
print(f"Max output: {caps.max_output_tokens}")

# Check temperature support
if caps.supports_temperature(0.7):
    print("Temperature 0.7 is supported")

# Check endpoint support
print(f"Chat API: {caps.supports_chat_api}")
print(f"Completions API: {caps.supports_completions_api}")
print(f"Responses API: {caps.supports_responses_api}")
```

### Registry Extension
```python
from mojentic.llm.gateways.openai_model_registry import (
    get_model_registry, ModelCapabilities, ModelType
)

registry = get_model_registry()

# Add new model with full capabilities
registry.register_model("gpt-6-preview", ModelCapabilities(
    model_type=ModelType.REASONING,
    supports_tools=True,
    supports_streaming=True,
    supports_vision=True,
    max_context_tokens=500000,
    max_output_tokens=100000,
    supported_temperatures=None,  # All temps supported
    supports_chat_api=True,
    supports_completions_api=False,
    supports_responses_api=True
))

# Add new pattern for unknown models
registry.register_pattern("gpt-6", ModelType.REASONING)
```

### Checking Model Lists
```python
from mojentic.llm.gateways.openai_model_registry import get_model_registry

registry = get_model_registry()

# Get all registered models
models = registry.get_registered_models()
print(f"Total models: {len(models)}")

# Check if a specific model is reasoning type
if registry.is_reasoning_model("gpt-5"):
    print("gpt-5 is a reasoning model")
```

## Migration Guide

### For Existing Code
No changes required! The infrastructure is backward compatible and handles parameter adaptation automatically.

### For New Models
1. Add to the registry in `openai_model_registry.py`, OR
2. Pattern matching will automatically classify models starting with known prefixes

### For Debugging Issues
1. Check logs for parameter adaptation messages
2. Use `registry.get_model_capabilities(model)` to inspect model classification
3. Enable debug logging to see detailed parameter handling

## Testing

Run the comprehensive test suite:
```bash
# Model registry tests
pytest src/mojentic/llm/gateways/openai_model_registry_spec.py

# Integration tests
pytest integration_checks/openai_gateway_spec.py

# Import validation
python -c "import mojentic.llm.gateways.openai_model_registry"
```

## Conclusion

The OpenAI gateway infrastructure provides:
- ✅ **Automatic parameter handling** — No more max_tokens vs max_completion_tokens errors
- ✅ **Endpoint awareness** — Know which API endpoints each model supports
- ✅ **Temperature validation** — Prevent invalid temperature values
- ✅ **Extensible architecture** — Easy to add new models and capabilities
- ✅ **Enhanced debugging** — Detailed logging for troubleshooting
- ✅ **Comprehensive testing** — Robust test coverage for reliability
- ✅ **Backward compatibility** — Existing code continues to work

This infrastructure ensures that users can work with any OpenAI model without worrying about parameter compatibility issues, while providing the flexibility to easily extend support for new models as they are released.
