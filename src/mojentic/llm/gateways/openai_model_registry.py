"""
OpenAI Model Registry for managing model-specific configurations and capabilities.

This module provides infrastructure for categorizing OpenAI models and managing
their specific parameter requirements and capabilities.
"""

from enum import Enum
from typing import Dict, Optional, List, TYPE_CHECKING
from dataclasses import dataclass

import structlog

if TYPE_CHECKING:
    pass

logger = structlog.get_logger()


class ModelType(Enum):
    """Classification of OpenAI model types based on their capabilities and parameters."""
    REASONING = "reasoning"  # Models like o1, o3 that use max_completion_tokens
    CHAT = "chat"  # Standard chat models that use max_tokens
    EMBEDDING = "embedding"  # Text embedding models
    MODERATION = "moderation"  # Content moderation models


@dataclass
class ModelCapabilities:
    """Defines the capabilities and parameter requirements for a model."""
    model_type: ModelType
    supports_tools: bool = True
    supports_streaming: bool = True
    supports_vision: bool = False
    max_context_tokens: Optional[int] = None
    max_output_tokens: Optional[int] = None
    supported_temperatures: Optional[List[float]] = None  # None means all temperatures supported
    supports_chat_api: bool = True
    supports_completions_api: bool = False
    supports_responses_api: bool = False

    def get_token_limit_param(self) -> str:
        """Get the correct parameter name for token limits based on model type."""
        if self.model_type == ModelType.REASONING:
            return "max_completion_tokens"
        return "max_tokens"

    def supports_temperature(self, temperature: float) -> bool:
        """Check if the model supports a specific temperature value."""
        if self.supported_temperatures is None:
            return True  # All temperatures supported if not restricted
        if self.supported_temperatures == []:
            return False  # No temperature values supported (parameter not allowed)
        return temperature in self.supported_temperatures


class OpenAIModelRegistry:
    """
    Registry for managing OpenAI model configurations and capabilities.

    This class provides a centralized way to manage model-specific configurations,
    parameter mappings, and capabilities for OpenAI models.
    """

    def __init__(self):
        self._models: Dict[str, ModelCapabilities] = {}
        self._pattern_mappings: Dict[str, ModelType] = {}
        self._initialize_default_models()

    def _initialize_default_models(self):
        """Initialize the registry with known OpenAI models and their capabilities."""

        # Reasoning Models (o1, o3, o4, gpt-5 series) - Updated 2026-02-04
        reasoning_models = [
            "o1", "o1-2024-12-17",
            "o1-pro", "o1-pro-2025-03-19",
            "o3", "o3-2025-04-16", "o3-deep-research", "o3-deep-research-2025-06-26",
            "o3-mini", "o3-mini-2025-01-31", "o3-pro", "o3-pro-2025-06-10",
            "o4-mini", "o4-mini-2025-04-16", "o4-mini-deep-research",
            "o4-mini-deep-research-2025-06-26",
            "gpt-5", "gpt-5-2025-08-07", "gpt-5-codex",
            "gpt-5-mini", "gpt-5-mini-2025-08-07", "gpt-5-nano", "gpt-5-nano-2025-08-07",
            "gpt-5-pro", "gpt-5-pro-2025-10-06",
            "gpt-5.1", "gpt-5.1-2025-11-13", "gpt-5.1-chat-latest",
            "gpt-5.2", "gpt-5.2-2025-12-11", "gpt-5.2-chat-latest"
        ]

        for model in reasoning_models:
            # Deep research models and GPT-5 might have different capabilities
            is_deep_research = "deep-research" in model
            is_gpt5 = "gpt-5" in model
            is_gpt5_1 = "gpt-5.1" in model
            is_gpt5_2 = "gpt-5.2" in model
            is_gpt5_pro = "gpt-5-pro" in model and not is_gpt5_2
            is_mini_or_nano = ("mini" in model or "nano" in model)
            is_chat_latest = "chat-latest" in model

            # ALL reasoning models now support tools and streaming (except gpt-5-pro which is responses-only)
            supports_tools = not is_gpt5_pro
            supports_streaming = not is_gpt5_pro

            # Set context and output tokens based on model tier
            if is_gpt5:
                context_tokens = 300000 if not is_mini_or_nano else 200000
                output_tokens = 50000 if not is_mini_or_nano else 32768
            elif is_deep_research:
                context_tokens = 200000
                output_tokens = 100000
            else:
                context_tokens = 128000
                output_tokens = 32768

            # Temperature restrictions based on model series
            # All reasoning models now support only temperature=1.0 (o3 now supports it too)
            if is_gpt5_1 and not is_chat_latest:
                # gpt-5.1 and gpt-5.1-2025-11-13 support all temperatures
                supported_temps = None
            elif is_gpt5_2 and not is_chat_latest:
                # gpt-5.2 and gpt-5.2-2025-12-11 support all temperatures
                supported_temps = None
            else:
                # All other reasoning models (including o1, o3, o4, gpt-5, and *-chat-latest) support only temp=1.0
                supported_temps = [1.0]

            # API endpoint support flags
            is_responses_only = "pro" in model or "deep-research" in model or model == "gpt-5-codex"
            is_both_endpoint = model in ("gpt-5.1", "gpt-5.1-2025-11-13")

            self._models[model] = ModelCapabilities(
                model_type=ModelType.REASONING,
                supports_tools=supports_tools,
                supports_streaming=supports_streaming,
                supports_vision=False,  # Vision support would need to be confirmed for GPT-5
                max_context_tokens=context_tokens,
                max_output_tokens=output_tokens,
                supported_temperatures=supported_temps,
                supports_chat_api=not is_responses_only,
                supports_completions_api=is_both_endpoint,
                supports_responses_api=is_responses_only
            )

        # Chat Models (GPT-4 and GPT-4.1 series) - Updated 2026-02-04
        # Note: Most GPT-5 series moved to reasoning models; gpt-5-chat-latest is chat
        gpt4_and_newer_models = [
            "chatgpt-4o-latest",
            "gpt-4", "gpt-4-0125-preview", "gpt-4-0613", "gpt-4-1106-preview",
            "gpt-4-turbo", "gpt-4-turbo-2024-04-09", "gpt-4-turbo-preview",
            "gpt-4.1", "gpt-4.1-2025-04-14", "gpt-4.1-mini", "gpt-4.1-mini-2025-04-14",
            "gpt-4.1-nano", "gpt-4.1-nano-2025-04-14",
            "gpt-4o", "gpt-4o-2024-05-13", "gpt-4o-2024-08-06", "gpt-4o-2024-11-20",
            "gpt-4o-audio-preview",
            "gpt-4o-audio-preview-2024-12-17", "gpt-4o-audio-preview-2025-06-03",
            "gpt-4o-mini", "gpt-4o-mini-2024-07-18",
            "gpt-4o-mini-audio-preview", "gpt-4o-mini-audio-preview-2024-12-17",
            "gpt-4o-mini-realtime-preview", "gpt-4o-mini-realtime-preview-2024-12-17",
            "gpt-4o-mini-search-preview", "gpt-4o-mini-search-preview-2025-03-11",
            "gpt-4o-mini-transcribe", "gpt-4o-mini-tts",
            "gpt-4o-realtime-preview", "gpt-4o-realtime-preview-2024-10-01",
            "gpt-4o-realtime-preview-2024-12-17", "gpt-4o-realtime-preview-2025-06-03",
            "gpt-4o-search-preview", "gpt-4o-search-preview-2025-03-11",
            "gpt-4o-transcribe",
            "gpt-5-chat-latest",
            "gpt-5-search-api", "gpt-5-search-api-2025-10-14"
        ]

        for model in gpt4_and_newer_models:
            # Determine capabilities based on model features
            is_chatgpt_latest = model == "chatgpt-4o-latest"
            is_mini_or_nano = ("mini" in model or "nano" in model)
            is_audio = "audio" in model or "realtime" in model or "transcribe" in model or "tts" in model
            is_search = "search" in model
            is_gpt41 = "gpt-4.1" in model
            is_gpt5_chat = model == "gpt-5-chat-latest"
            is_gpt5_search = "gpt-5-search-api" in model
            is_nano_base = model == "gpt-4.1-nano"
            # Note: Keep vision=True for gpt-4o models (audit probe limitation with 1x1 PNG)
            # Exclude chatgpt-4o-latest, audio/search/transcribe/tts/realtime variants
            vision_support = ("gpt-4o" in model and not is_chatgpt_latest and not is_audio and not is_search)

            # Tool support: disabled for audio models, search models, chatgpt-4o-latest, and gpt-4.1-nano
            supports_tools = not (is_audio or is_search or is_chatgpt_latest or is_nano_base)
            # Streaming: disabled for audio models only
            supports_streaming = not is_audio
            # Temperature restrictions for search models
            supported_temps = [] if is_search else None

            # Set context and output tokens based on model tier
            if is_gpt5_chat or is_gpt5_search:
                context_tokens = 300000
                output_tokens = 50000
            elif is_gpt41:
                context_tokens = 200000 if not is_mini_or_nano else 128000
                output_tokens = 32768 if not is_mini_or_nano else 16384
            elif "gpt-4o" in model:
                context_tokens = 128000
                output_tokens = 16384
            else:  # GPT-4 series
                context_tokens = 32000
                output_tokens = 8192

            # API endpoint support flags
            is_both_endpoint = model in ("gpt-4.1-nano", "gpt-4.1-nano-2025-04-14",
                                         "gpt-4o-mini", "gpt-4o-mini-2024-07-18")

            self._models[model] = ModelCapabilities(
                model_type=ModelType.CHAT,
                supports_tools=supports_tools,
                supports_streaming=supports_streaming,
                supports_vision=vision_support,
                max_context_tokens=context_tokens,
                max_output_tokens=output_tokens,
                supported_temperatures=supported_temps,
                supports_completions_api=is_both_endpoint
            )

        # Chat Models (GPT-3.5 series) - Updated 2026-02-04
        gpt35_models = [
            "gpt-3.5-turbo", "gpt-3.5-turbo-0125", "gpt-3.5-turbo-1106",
            "gpt-3.5-turbo-16k", "gpt-3.5-turbo-instruct", "gpt-3.5-turbo-instruct-0914"
        ]

        for model in gpt35_models:
            is_instruct = "instruct" in model
            context_tokens = 16385 if "16k" not in model else 16385
            self._models[model] = ModelCapabilities(
                model_type=ModelType.CHAT,
                supports_tools=not is_instruct,  # Instruct models don't support tools
                supports_streaming=not is_instruct,  # Instruct models don't support streaming
                supports_vision=False,
                max_context_tokens=context_tokens,
                max_output_tokens=4096,
                supports_chat_api=not is_instruct,
                supports_completions_api=is_instruct
            )

        # Embedding Models - Updated 2026-02-04
        embedding_models = [
            "text-embedding-3-large", "text-embedding-3-small", "text-embedding-ada-002"
        ]

        for model in embedding_models:
            self._models[model] = ModelCapabilities(
                model_type=ModelType.EMBEDDING,
                supports_tools=False,
                supports_streaming=False,
                supports_vision=False,
                supports_chat_api=False
            )

        # Legacy & Codex Models - Updated 2026-02-05
        self._models["babbage-002"] = ModelCapabilities(
            model_type=ModelType.CHAT,
            supports_tools=False,
            supports_streaming=False,
            supports_vision=False,
            supports_chat_api=False,
            supports_completions_api=True
        )

        self._models["davinci-002"] = ModelCapabilities(
            model_type=ModelType.CHAT,
            supports_tools=False,
            supports_streaming=False,
            supports_vision=False,
            supports_chat_api=False,
            supports_completions_api=True
        )

        self._models["gpt-5.1-codex-mini"] = ModelCapabilities(
            model_type=ModelType.REASONING,
            supports_tools=False,
            supports_streaming=False,
            supports_vision=False,
            max_context_tokens=128000,
            max_output_tokens=32768,
            supported_temperatures=[1.0],
            supports_chat_api=False,
            supports_completions_api=True
        )

        self._models["codex-mini-latest"] = ModelCapabilities(
            model_type=ModelType.REASONING,
            supports_tools=False,
            supports_streaming=False,
            supports_vision=False,
            max_context_tokens=128000,
            max_output_tokens=32768,
            supported_temperatures=[1.0],
            supports_chat_api=False,
            supports_responses_api=True
        )

        # Pattern mappings for unknown models - Updated 2026-02-04
        self._pattern_mappings = {
            "o1": ModelType.REASONING,
            "o3": ModelType.REASONING,
            "o4": ModelType.REASONING,
            "gpt-5": ModelType.REASONING,  # GPT-5 is a reasoning model
            "gpt-5.1": ModelType.REASONING,
            "gpt-5.2": ModelType.REASONING,
            "gpt-4": ModelType.CHAT,
            "gpt-4.1": ModelType.CHAT,
            "gpt-3.5": ModelType.CHAT,
            "chatgpt": ModelType.CHAT,
            "text-embedding": ModelType.EMBEDDING,
            "text-moderation": ModelType.MODERATION
        }

    def get_model_capabilities(self, model_name: str) -> ModelCapabilities:
        """
        Get the capabilities for a specific model.

        Parameters
        ----------
        model_name : str
            The name of the model to look up.

        Returns
        -------
        ModelCapabilities
            The capabilities for the model.
        """
        # Direct lookup first
        if model_name in self._models:
            return self._models[model_name]

        # Pattern matching for unknown models
        model_lower = model_name.lower()
        for pattern, model_type in self._pattern_mappings.items():
            if pattern in model_lower:
                logger.warning(
                    "Using pattern matching for unknown model",
                    model=model_name,
                    pattern=pattern,
                    inferred_type=model_type.value
                )
                # Return default capabilities for the inferred type
                return self._get_default_capabilities_for_type(model_type)

        # Default to chat model if no pattern matches
        logger.warning(
            "Unknown model, defaulting to chat model capabilities",
            model=model_name
        )
        return self._get_default_capabilities_for_type(ModelType.CHAT)

    def _get_default_capabilities_for_type(self, model_type: ModelType) -> ModelCapabilities:
        """Get default capabilities for a model type."""
        if model_type == ModelType.REASONING:
            return ModelCapabilities(
                model_type=ModelType.REASONING,
                supports_tools=False,
                supports_streaming=False,
                supports_vision=False,
                supports_chat_api=True,
                supports_completions_api=False,
                supports_responses_api=False
            )
        elif model_type == ModelType.CHAT:
            return ModelCapabilities(
                model_type=ModelType.CHAT,
                supports_tools=True,
                supports_streaming=True,
                supports_vision=False,
                supports_chat_api=True,
                supports_completions_api=False,
                supports_responses_api=False
            )
        elif model_type == ModelType.EMBEDDING:
            return ModelCapabilities(
                model_type=ModelType.EMBEDDING,
                supports_tools=False,
                supports_streaming=False,
                supports_vision=False,
                supports_chat_api=False,
                supports_completions_api=False,
                supports_responses_api=False
            )
        else:  # MODERATION
            return ModelCapabilities(
                model_type=ModelType.MODERATION,
                supports_tools=False,
                supports_streaming=False,
                supports_vision=False,
                supports_chat_api=False,
                supports_completions_api=False,
                supports_responses_api=False
            )

    def is_reasoning_model(self, model_name: str) -> bool:
        """
        Check if a model is a reasoning model.

        Parameters
        ----------
        model_name : str
            The name of the model to check.

        Returns
        -------
        bool
            True if the model is a reasoning model, False otherwise.
        """
        capabilities = self.get_model_capabilities(model_name)
        return capabilities.model_type == ModelType.REASONING

    def get_registered_models(self) -> List[str]:
        """
        Get a list of all explicitly registered models.

        Returns
        -------
        List[str]
            List of registered model names.
        """
        return list(self._models.keys())

    def register_model(self, model_name: str, capabilities: ModelCapabilities):
        """
        Register a new model with its capabilities.

        Parameters
        ----------
        model_name : str
            The name of the model to register.
        capabilities : ModelCapabilities
            The capabilities of the model.
        """
        self._models[model_name] = capabilities
        logger.info("Registered new model", model=model_name, type=capabilities.model_type.value)

    def register_pattern(self, pattern: str, model_type: ModelType):
        """
        Register a pattern for inferring model types.

        Parameters
        ----------
        pattern : str
            The pattern to match in model names.
        model_type : ModelType
            The type to infer for matching models.
        """
        self._pattern_mappings[pattern] = model_type
        logger.info("Registered new pattern", pattern=pattern, type=model_type.value)


# Global registry instance
_registry = OpenAIModelRegistry()


def get_model_registry() -> OpenAIModelRegistry:
    """Get the global OpenAI model registry instance."""
    return _registry
