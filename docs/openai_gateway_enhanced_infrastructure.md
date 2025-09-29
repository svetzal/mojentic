# OpenAI Gateway Enhanced Infrastructure

## Overview

This document describes the enhanced infrastructure implemented for the OpenAI gateway to handle the differences between reasoning models (like o1, o3) and chat models (like GPT-4) in terms of parameter requirements and capabilities.

## Problem Statement

OpenAI's reasoning models require different parameters than chat models:
- **Reasoning models** (o1, o3, o4 series): Use `max_completion_tokens` instead of `max_tokens`
- **Chat models** (GPT-4, GPT-3.5 series): Use `max_tokens`

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
- ✅ Pre-populated with known OpenAI models
- ✅ Pattern matching for unknown models
- ✅ Runtime registration of new models and patterns
- ✅ Automatic parameter name resolution (`get_token_limit_param()`)

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

## Key Benefits

### 1. **Automatic Parameter Handling**
```python
# Before: Manual parameter management required
# After: Automatic adaptation based on model type
gateway.complete(
    model="o1-mini",  # Reasoning model
    messages=messages,
    max_tokens=1000   # Automatically converted to max_completion_tokens
)
```

### 2. **Enhanced Debugging**
```
INFO: Converted token limit parameter for model
  model=o1-mini
  from_param=max_tokens
  to_param=max_completion_tokens
  value=1000
```

### 3. **Extensible Architecture**
```python
# Easy to add new models
registry.register_model("o5-preview", capabilities)

# Easy to add new patterns
registry.register_pattern("claude", ModelType.CHAT)
```

### 4. **Better Error Messages**
```
ValueError: Reasoning model 'o1-mini' requires 'max_completion_tokens' instead of 'max_tokens'. This should be handled automatically by parameter adaptation.
```

## Model Classification

### Reasoning Models
- **Pattern**: o1*, o3*, o4*
- **Parameter**: `max_completion_tokens`
- **Tools**: Not supported (automatically removed)
- **Streaming**: Not supported

### Chat Models
- **Pattern**: gpt-4*, gpt-3.5*
- **Parameter**: `max_tokens`
- **Tools**: Supported
- **Streaming**: Supported

### Unknown Models
- **Fallback**: Default to chat model capabilities with warning
- **Logging**: Pattern matching attempts logged for debugging

## Usage Examples

### Basic Usage (Automatic)
```python
from mojentic.llm.gateways.openai import OpenAIGateway

gateway = OpenAIGateway(api_key="your-key")

# Works automatically for both model types
response = gateway.complete(
    model="o1-mini",  # or "gpt-4o"
    messages=messages,
    max_tokens=1000   # Automatically adapted as needed
)
```

### Registry Extension
```python
from mojentic.llm.gateways.openai_model_registry import get_model_registry, ModelCapabilities, ModelType

registry = get_model_registry()

# Add new model
registry.register_model("custom-model", ModelCapabilities(
    model_type=ModelType.REASONING,
    supports_tools=True,
    max_output_tokens=50000
))

# Add new pattern
registry.register_pattern("anthropic", ModelType.CHAT)
```

## Migration Guide

### For Existing Code
No changes required! The new infrastructure is backward compatible and handles parameter adaptation automatically.

### For New Reasoning Models
1. Add to the registry in `openai_model_registry.py`, OR
2. The pattern matching will automatically classify models starting with "o1", "o3", "o4"

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

# Demo
python src/_examples/openai_gateway_enhanced_demo.py
```

## Future Enhancements

### Potential Improvements
- [ ] Auto-discovery of model capabilities via OpenAI API
- [ ] Configuration file-based model registry
- [ ] Model capability caching
- [ ] Integration with LLM model selection logic

### Adding New Model Types
The architecture easily supports new model types:
```python
class ModelType(Enum):
    REASONING = "reasoning"
    CHAT = "chat"
    EMBEDDING = "embedding"
    MODERATION = "moderation"
    IMAGE_GENERATION = "image_generation"  # Future
    CODE_GENERATION = "code_generation"    # Future
```

## Conclusion

The enhanced OpenAI gateway infrastructure provides:
- ✅ **Automatic parameter handling** - No more max_tokens vs max_completion_tokens errors
- ✅ **Extensible architecture** - Easy to add new models and capabilities
- ✅ **Enhanced debugging** - Detailed logging for troubleshooting
- ✅ **Comprehensive testing** - Robust test coverage for reliability
- ✅ **Backward compatibility** - Existing code continues to work

This infrastructure ensures that users can work with any OpenAI model without worrying about parameter compatibility issues, while providing the flexibility to easily extend support for new models as they are released.