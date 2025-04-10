# Integration Tests for LLM Gateways

This directory contains integration tests for the LLM gateways in the Mojentic project. These tests verify that the gateways correctly interact with their respective LLM services.

## Unified Test Plan

All LLM gateways should implement the following tests to ensure consistent behavior across different providers.

### Basic Functionality

1. **Initialization**
   - Test initialization with appropriate parameters (API key, host, etc.)

2. **Core Features**
   - Test completion with simple messages
   - Test getting available models
   - Test calculating embeddings

### Advanced Features

1. **Structured Output**
   - Test completion with object model validation

2. **Tool Integration**
   - Test completion with tool calls

3. **Error Handling**
   - Test handling of errors (invalid credentials, model not found, etc.)

### Gateway-Specific Features

Some gateways have unique features that should be tested when available:

1. **Streaming** (Ollama)
   - Test streaming completion

2. **Model Management** (Ollama)
   - Test pulling models

## Implementation Notes

- Tests for features not yet implemented in a specific gateway should be temporarily disabled with appropriate comments.
- All gateways should eventually implement all common features to maintain symmetry.
- Gateway-specific features should be clearly marked as such.

## Test Implementation

The tests are implemented using pytest and follow the specification-style approach used throughout the Mojentic project:

- Test files are named with "*_spec.py" suffix
- Test classes are prefixed with "Describe"
- Test methods are prefixed with "should_"
- Tests follow the Given-When-Then pattern

## Running the Tests

To run the integration tests:

```bash
# Run all integration tests
pytest integration_checks/

# Run specific gateway tests
pytest integration_checks/openai_gateway_spec.py
pytest integration_checks/ollama_gateway_spec.py
```

## Configuration

The tests require configuration for the LLM services:

### OpenAI

Set the `OPENAI_API_KEY` environment variable to your OpenAI API key:

```bash
export OPENAI_API_KEY=your_api_key_here
```

### Ollama

Ensure that Ollama is running locally on the default port (11434). If you're using a different host or port, set the `OLLAMA_HOST` environment variable:

```bash
export OLLAMA_HOST=http://your-ollama-host:port
```

The tests will use small models to minimize resource usage and API costs.
