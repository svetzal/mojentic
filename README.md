# Mojentic

Mojentic is a framework that provides a simple and flexible way to interact with Large Language Models (LLMs). It offers integration with various LLM providers and includes tools for structured output generation, task automation, and more. The future direction is to facilitate a team of agents, but the current focus is on robust LLM interaction capabilities.

[![GitHub](https://img.shields.io/github/license/svetzal/mojentic)](LICENSE.md)
[![Python Version](https://img.shields.io/badge/python-3.11%2B-blue)](https://www.python.org/downloads/)
[![Documentation](https://img.shields.io/badge/docs-latest-brightgreen)](https://svetzal.github.io/mojentic/)

## 🚀 Features

- **LLM Integration**: Support for multiple LLM providers (OpenAI, Ollama)
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

```bash
# Install from PyPI
pip install mojentic
```

Or install from source

```bash
git clone https://github.com/svetzal/mojentic.git
cd mojentic
pip install -e .
```

## 🚦 Quick Start

```python
from mojentic.llm import LLMBroker
from mojentic.llm.gateways import OpenAIGateway, OllamaGateway
from mojentic.llm.gateways.models import LLMMessage
from mojentic.llm.tools.date_resolver import ResolveDateTool
from pydantic import BaseModel, Field

# Initialize with OpenAI
openai_llm = LLMBroker(model="gpt-4o", gateway=OpenAIGateway(api_key="your_api_key"))

# Or use Ollama for local LLMs
ollama_llm = LLMBroker(model="llama3")

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

# Install dependencies
pip install -e ".[dev]"

# Run tests
pytest
```

## ⚠️ Project Status

While the Layer 1 API (LLMBroker, LLMGateway, tool use) has stabilized, the Layer 2 agentic capabilities are under heavy development and will likely change significantly.

## 📄 License

This code is Copyright 2025 Mojility, Inc. and is freely provided under the terms of the [MIT license](LICENSE.md).
