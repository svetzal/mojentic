"""
Tests for the OpenAI Model Registry system.
"""

import pytest
from mojentic.llm.gateways.openai_model_registry import (
    OpenAIModelRegistry,
    ModelType,
    ModelCapabilities,
    get_model_registry
)


class DescribeOpenAIModelRegistry:
    """Specification for the OpenAI Model Registry."""

    def should_initialize_with_default_models(self):
        """
        Given a new model registry
        When initialized
        Then it should contain default models for all major OpenAI model families
        """
        registry = OpenAIModelRegistry()
        registered_models = registry.get_registered_models()

        # Check that we have reasoning models
        assert "o1" in registered_models
        assert "o1-mini" in registered_models

        # Check that we have chat models
        assert "gpt-4o" in registered_models
        assert "gpt-4o-mini" in registered_models
        assert "gpt-3.5-turbo" in registered_models

        # Check that we have embedding models
        assert "text-embedding-3-large" in registered_models
        assert "text-embedding-3-small" in registered_models

    def should_identify_reasoning_models_correctly(self):
        """
        Given various model names
        When checking if they are reasoning models
        Then it should correctly classify known reasoning models
        """
        registry = OpenAIModelRegistry()

        # Test known reasoning models
        assert registry.is_reasoning_model("o1-preview") is True
        assert registry.is_reasoning_model("o1-mini") is True
        assert registry.is_reasoning_model("o3-mini") is True

        # Test chat models
        assert registry.is_reasoning_model("gpt-4o") is False
        assert registry.is_reasoning_model("gpt-4o-mini") is False
        assert registry.is_reasoning_model("gpt-3.5-turbo") is False

    def should_use_pattern_matching_for_unknown_models(self):
        """
        Given an unknown model name that matches a pattern
        When getting model capabilities
        Then it should infer the correct model type
        """
        registry = OpenAIModelRegistry()

        # Test unknown reasoning model
        capabilities = registry.get_model_capabilities("o1-super-new")
        assert capabilities.model_type == ModelType.REASONING
        assert capabilities.get_token_limit_param() == "max_completion_tokens"

        # Test unknown chat model
        capabilities = registry.get_model_capabilities("gpt-4-future")
        assert capabilities.model_type == ModelType.CHAT
        assert capabilities.get_token_limit_param() == "max_tokens"

    def should_return_correct_token_limit_parameters(self):
        """
        Given models of different types
        When getting their token limit parameters
        Then it should return the correct parameter name
        """
        registry = OpenAIModelRegistry()

        # Reasoning models should use max_completion_tokens
        o1_capabilities = registry.get_model_capabilities("o1-mini")
        assert o1_capabilities.get_token_limit_param() == "max_completion_tokens"

        # Chat models should use max_tokens
        gpt4_capabilities = registry.get_model_capabilities("gpt-4o")
        assert gpt4_capabilities.get_token_limit_param() == "max_tokens"

    def should_allow_registering_new_models(self):
        """
        Given a new model with specific capabilities
        When registering it in the registry
        Then it should be available for lookup
        """
        registry = OpenAIModelRegistry()

        new_capabilities = ModelCapabilities(
            model_type=ModelType.REASONING,
            supports_tools=True,
            supports_streaming=True,
            max_output_tokens=50000
        )

        registry.register_model("o5-preview", new_capabilities)

        retrieved_capabilities = registry.get_model_capabilities("o5-preview")
        assert retrieved_capabilities.model_type == ModelType.REASONING
        assert retrieved_capabilities.supports_tools is True
        assert retrieved_capabilities.max_output_tokens == 50000

    def should_allow_registering_new_patterns(self):
        """
        Given a new pattern for model type inference
        When registering it in the registry
        Then it should be used for unknown models matching the pattern
        """
        registry = OpenAIModelRegistry()

        registry.register_pattern("claude", ModelType.CHAT)

        capabilities = registry.get_model_capabilities("claude-3-opus")
        assert capabilities.model_type == ModelType.CHAT

    def should_handle_completely_unknown_models(self):
        """
        Given a completely unknown model name with no matching patterns
        When getting model capabilities
        Then it should default to chat model capabilities
        """
        registry = OpenAIModelRegistry()

        capabilities = registry.get_model_capabilities("completely-unknown-model-xyz")
        assert capabilities.model_type == ModelType.CHAT
        assert capabilities.get_token_limit_param() == "max_tokens"

    def should_provide_global_registry_instance(self):
        """
        Given the global registry function
        When called multiple times
        Then it should return the same instance
        """
        registry1 = get_model_registry()
        registry2 = get_model_registry()

        assert registry1 is registry2

    def should_handle_model_capabilities_dataclass_correctly(self):
        """
        Given model capabilities
        When created with different parameters
        Then it should handle defaults and customizations correctly
        """
        # Test with defaults
        default_caps = ModelCapabilities(model_type=ModelType.CHAT)
        assert default_caps.supports_tools is True
        assert default_caps.supports_streaming is True
        assert default_caps.supports_vision is False

        # Test with custom values
        custom_caps = ModelCapabilities(
            model_type=ModelType.REASONING,
            supports_tools=False,
            supports_vision=True,
            max_context_tokens=100000
        )
        assert custom_caps.supports_tools is False
        assert custom_caps.supports_vision is True
        assert custom_caps.max_context_tokens == 100000

    def should_have_correct_model_type_enum_values(self):
        """
        Given the ModelType enum
        When accessing its values
        Then it should have all expected model types
        """
        assert ModelType.REASONING.value == "reasoning"
        assert ModelType.CHAT.value == "chat"
        assert ModelType.EMBEDDING.value == "embedding"
        assert ModelType.MODERATION.value == "moderation"