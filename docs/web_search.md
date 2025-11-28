# Web Search

The `mojentic.llm.tools.WebSearchTool` enables agents to access real-time information from the internet.

## Configuration

The web search tool typically requires an API key for a search provider (e.g., Tavily, Serper).

```python
import os
os.environ["TAVILY_API_KEY"] = "your-api-key"
```

## Usage

```python
from mojentic.llm import LLMBroker, LLMMessage
from mojentic.llm.gateways import OllamaGateway
from mojentic.llm.tools import WebSearchTool

# Initialize broker
broker = LLMBroker(model="qwen3:32b", gateway=OllamaGateway())

# Register the tool
tools = [WebSearchTool(provider="tavily")]

# Ask a question requiring up-to-date info
messages = [
    LLMMessage(content="What is the current stock price of Apple?")
]

response = broker.generate(messages, tools=tools)
print(response)
```

## Supported Providers

- **Tavily**: Optimized for LLM agents
- **Serper**: Google Search API
- **DuckDuckGo**: Privacy-focused search (no API key required for basic usage)
