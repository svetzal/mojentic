# Mojentic

Mojentic is a framework that provides a simple and flexible way to interact with Large Language Models (LLMs). It offers integration with various LLM providers and includes tools for structured output generation, task automation, and more. With comprehensive support for all OpenAI models including GPT-5 and automatic parameter adaptation, Mojentic handles the complexities of different model types seamlessly. The future direction is to facilitate a team of agents, but the current focus is on robust LLM interaction capabilities.

[![GitHub](https://img.shields.io/github/license/svetzal/mojentic)](LICENSE.md)
[![Python Version](https://img.shields.io/badge/python-3.11%2B-blue)](https://www.python.org/downloads/)
[![Documentation](https://img.shields.io/badge/docs-latest-brightgreen)](https://svetzal.github.io/mojentic/)

## 🚀 Features

- **LLM Integration**: Support for multiple LLM providers (OpenAI, Ollama, Anthropic, oMLX)
- **Latest OpenAI Models**: Full support for GPT-5, GPT-4.1, and all reasoning models (o1, o3, o4 series)
- **Automatic Model Adaptation**: Seamless parameter handling across different OpenAI model types
- **Structured Output**: Generate structured data from LLM responses using Pydantic models
- **Tools Integration**: Utilities for date resolution, image analysis, and more
- **Multi-modal Capabilities**: Process and analyze images alongside text
- **Simple API**: Easy-to-use interface for LLM interactions
- **Future Development**: Working towards an agent framework with team coordination capabilities

## 📋 Requirements

- Python 3.11+
- Ollama (for local LLM support)
  - Required models: `mxbai-embed-large` for embeddings

## 🔧 Installation

We recommend using [uv](https://docs.astral.sh/uv/) for fast, reliable Python project management.

```bash
# Install from PyPI using uv
uv pip install mojentic

# Or with pip
pip install mojentic
```

Or install from source:

```bash
git clone https://github.com/svetzal/mojentic.git
cd mojentic

# Using uv (recommended)
uv sync

# Or with pip
pip install -e .
```

## 🚦 Quick Start

```python
from mojentic.llm import LLMBroker
from mojentic.llm.gateways import OpenAIGateway, OllamaGateway
from mojentic.llm.gateways.models import LLMMessage
from mojentic.llm.tools.date_resolver import ResolveDateTool
from pydantic import BaseModel, Field

# Initialize with OpenAI (supports all models including GPT-5, GPT-4.1, reasoning models)
openai_llm = LLMBroker(model="gpt-5", gateway=OpenAIGateway(api_key="your_api_key"))
# Or use other models: "gpt-4o", "gpt-4.1", "o1-mini", "o3-mini", etc.

# Or use Ollama for local LLMs
ollama_llm = LLMBroker(model="qwen3:32b")

# Simple text generation
result = openai_llm.generate(messages=[LLMMessage(content='Hello, how are you?')])
print(result)

# Generate structured output
class Sentiment(BaseModel):
    label: str = Field(..., description="Label for the sentiment")

sentiment = openai_llm.generate_object(
    messages=[LLMMessage(content="Hello, how are you?")],
    object_model=Sentiment
)
print(sentiment.label)

# Use tools with the LLM
result = openai_llm.generate(
    messages=[LLMMessage(content='What is the date on Friday?')],
    tools=[ResolveDateTool()]
)
print(result)

# Image analysis
result = openai_llm.generate(messages=[
    LLMMessage(content='What is in this image?', image_paths=['path/to/image.jpg'])
])
print(result)
```

## 🔑 OpenAI configuration

OpenAIGateway now supports environment-variable defaults so you can get started without hardcoding secrets:

- If you omit `api_key`, it will use the `OPENAI_API_KEY` environment variable.
- If you omit `base_url`, it will use the `OPENAI_API_ENDPOINT` environment variable (useful for custom endpoints like Azure/OpenAI-compatible proxies).
- Precedence: values you pass explicitly to `OpenAIGateway(api_key=..., base_url=...)` always override environment variables.

Examples:

```python
from mojentic.llm import LLMBroker
from mojentic.llm.gateways import OpenAIGateway

# 1) Easiest: rely on environment variables
#    export OPENAI_API_KEY=sk-...
#    export OPENAI_API_ENDPOINT=https://api.openai.com/v1   # optional
llm = LLMBroker(
    model="gpt-4o-mini",
    gateway=OpenAIGateway()  # picks up OPENAI_API_KEY/OPENAI_API_ENDPOINT automatically
)

# 2) Explicitly override one or both values
llm = LLMBroker(
    model="gpt-4o-mini",
    gateway=OpenAIGateway(api_key="your_key", base_url="https://api.openai.com/v1")
)
```

## 🤖 OpenAI Model Support

The framework automatically handles parameter differences between model types, so you can switch between any models without code changes.

### Model-Specific Limitations

Some models have specific parameter restrictions that are automatically handled:

- **GPT-5 Series**: Only supports `temperature=1.0` (default). Other temperature values are automatically adjusted with a warning.
- **o1 & o4 Series**: Only supports `temperature=1.0` (default). Other temperature values are automatically adjusted with a warning.
- **o3 Series**: Does not support the `temperature` parameter at all. The parameter is automatically removed with a warning.
- **All Reasoning Models** (o1, o3, o4, GPT-5): Use `max_completion_tokens` instead of `max_tokens`, and have limited tool support.

The framework will automatically adapt parameters and log warnings when unsupported values are provided.

## 🏗️ Project Structure

```
src/
├── mojentic/           # Main package
│   ├── llm/            # LLM integration (primary focus)
│   │   ├── gateways/   # LLM provider adapters (OpenAI, Ollama)
│   │   ├── registry/   # Model registration
│   │   └── tools/      # Utility tools for LLMs
│   ├── agents/         # Agent implementations (under development)
│   ├── context/        # Shared memory and context (under development)
├── _examples/          # Usage examples
```

The primary focus is currently on the `llm` module, which provides robust capabilities for interacting with various LLM providers.

## 📚 Documentation

Visit [the documentation](https://svetzal.github.io/mojentic/) for comprehensive guides, API reference, and examples.

## 🧪 Development

```bash
# Clone the repository
git clone https://github.com/svetzal/mojentic.git
cd mojentic

# Using uv (recommended)
uv sync --extra dev

# Or with pip
pip install -e ".[dev]"

# Run tests
pytest

# Quality checks
flake8 src          # Linting
bandit -r src       # Security scan
pip-audit           # Dependency vulnerabilities
```

## ✅ Project Status

The agentic aspects of this framework are in the highest state of flux. The first layer has stabilized, as have the simpler parts of the second layer, and we're working on the stability of the asynchronous pubsub architecture. We expect Python 3.14 will be the real enabler for the async aspects of the second layer.

## 📄 License

This code is Copyright 2025 Mojility, Inc. and is freely provided under the terms of the [MIT license](LICENSE.md).

### Opt-in Ollama recovery

Ollama ordinary and structured completions can use an explicit `RecoveryPolicy`
through the existing broker and chat session APIs. Retries require caller admission
when inference termination is unknown. See [the migration guide](docs/transient_recovery.md)
for bounded delays, cancellation, safe reports, and caller-owned wire capture.
Streaming and other adapter recovery remain pending.
