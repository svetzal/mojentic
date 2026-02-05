from typing import Optional, Literal
from pydantic import BaseModel, Field


class CompletionConfig(BaseModel):
    """
    Configuration object for LLM completion requests.

    This model provides a unified way to configure LLM behavior across different
    providers and models. It replaces loose kwargs with a structured configuration
    object.

    Attributes
    ----------
    temperature : float
        Controls randomness in the output. Higher values (e.g., 1.5) make output
        more random, while lower values (e.g., 0.1) make it more deterministic.
        Defaults to 1.0.
    num_ctx : int
        The number of context tokens to use. This sets the context window size.
        Defaults to 32768.
    max_tokens : int
        The maximum number of tokens to generate in the response.
        Defaults to 16384.
    num_predict : int
        The number of tokens to predict. A value of -1 means no limit.
        Defaults to -1.
    reasoning_effort : Optional[Literal["low", "medium", "high"]]
        Controls the reasoning effort level for models that support extended thinking.
        - "low": Quick, minimal reasoning
        - "medium": Balanced reasoning effort
        - "high": Deep, thorough reasoning
        Provider-specific behavior:
        - Ollama: Maps to `think: true` parameter for all levels
        - OpenAI: Maps to `reasoning_effort` API parameter for reasoning models
        Defaults to None (no extended reasoning).
    """

    temperature: float = Field(
        default=1.0,
        description="Temperature for sampling (higher = more random)"
    )
    num_ctx: int = Field(
        default=32768,
        description="Number of context tokens"
    )
    max_tokens: int = Field(
        default=16384,
        description="Maximum tokens to generate"
    )
    num_predict: int = Field(
        default=-1,
        description="Number of tokens to predict (-1 = no limit)"
    )
    reasoning_effort: Optional[Literal["low", "medium", "high"]] = Field(
        default=None,
        description="Reasoning effort level for extended thinking"
    )
