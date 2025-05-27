"""
Mojentic LLM gateways module for connecting to various LLM providers.
"""

# Gateway implementations
from .llm_gateway import LLMGateway
from .ollama import OllamaGateway
from .openai import OpenAIGateway
from .anthropic import AnthropicGateway
from .file_gateway import FileGateway
from .embeddings_gateway import EmbeddingsGateway
from .tokenizer_gateway import TokenizerGateway

# Message adapters
from .anthropic_messages_adapter import adapt_messages_to_anthropic
from .ollama_messages_adapter import adapt_messages_to_ollama
from .openai_messages_adapter import adapt_messages_to_openai

# Common models
from .models import (
    LLMMessage,
    MessageRole,
    LLMGatewayResponse,
    LLMToolCall
)
