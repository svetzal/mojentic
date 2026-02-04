"""
Tests for the OpenAI Model Registry system.
"""

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

        # Check that we have reasoning models (o1-mini removed in 2026-02-04 audit)
        assert "o1" in registered_models
        assert "o3" in registered_models
        assert "gpt-5" in registered_models

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

        # Test known reasoning models (o1-mini removed, o1-preview uses pattern matching)
        assert registry.is_reasoning_model("o1") is True
        assert registry.is_reasoning_model("o3-mini") is True
        assert registry.is_reasoning_model("gpt-5") is True
        assert registry.is_reasoning_model("gpt-5.1") is True

        # Test chat models
        assert registry.is_reasoning_model("gpt-4o") is False
        assert registry.is_reasoning_model("gpt-4o-mini") is False
        assert registry.is_reasoning_model("gpt-3.5-turbo") is False
        assert registry.is_reasoning_model("gpt-5-chat-latest") is False

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
        o1_capabilities = registry.get_model_capabilities("o1")
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

    def should_support_tools_and_streaming_for_all_reasoning_models(self):
        """
        Given reasoning models as of 2026-02-04 audit
        When checking their capabilities
        Then all should support tools and streaming except gpt-5-pro
        """
        registry = OpenAIModelRegistry()

        # All o1/o3/o4 models now support tools and streaming
        o1_caps = registry.get_model_capabilities("o1")
        assert o1_caps.supports_tools is True
        assert o1_caps.supports_streaming is True

        o3_caps = registry.get_model_capabilities("o3")
        assert o3_caps.supports_tools is True
        assert o3_caps.supports_streaming is True

        o3_mini_caps = registry.get_model_capabilities("o3-mini")
        assert o3_mini_caps.supports_tools is True
        assert o3_mini_caps.supports_streaming is True

        # GPT-5 family (except gpt-5-pro) supports tools and streaming
        gpt5_caps = registry.get_model_capabilities("gpt-5")
        assert gpt5_caps.supports_tools is True
        assert gpt5_caps.supports_streaming is True

        # gpt-5-pro is responses-only, no tools/streaming
        gpt5_pro_caps = registry.get_model_capabilities("gpt-5-pro")
        assert gpt5_pro_caps.supports_tools is False
        assert gpt5_pro_caps.supports_streaming is False

    def should_support_temperature_1_0_only_for_most_reasoning_models(self):
        """
        Given reasoning models as of 2026-02-04 audit
        When checking temperature support
        Then most should support only temperature=1.0, except gpt-5.1/5.2 base models
        """
        registry = OpenAIModelRegistry()

        # o1/o3/o4 series support only temperature=1.0
        o1_caps = registry.get_model_capabilities("o1")
        assert o1_caps.supported_temperatures == [1.0]
        assert o1_caps.supports_temperature(1.0) is True
        assert o1_caps.supports_temperature(0.7) is False

        o3_caps = registry.get_model_capabilities("o3")
        assert o3_caps.supported_temperatures == [1.0]

        # gpt-5.1 and gpt-5.1-2025-11-13 support all temperatures
        gpt5_1_caps = registry.get_model_capabilities("gpt-5.1")
        assert gpt5_1_caps.supported_temperatures is None
        assert gpt5_1_caps.supports_temperature(0.7) is True
        assert gpt5_1_caps.supports_temperature(1.0) is True

        # gpt-5.1-chat-latest supports only temperature=1.0
        gpt5_1_chat_caps = registry.get_model_capabilities("gpt-5.1-chat-latest")
        assert gpt5_1_chat_caps.supported_temperatures == [1.0]

        # gpt-5.2 and gpt-5.2-2025-12-11 support all temperatures
        gpt5_2_caps = registry.get_model_capabilities("gpt-5.2")
        assert gpt5_2_caps.supported_temperatures is None

        # gpt-5.2-chat-latest supports only temperature=1.0
        gpt5_2_chat_caps = registry.get_model_capabilities("gpt-5.2-chat-latest")
        assert gpt5_2_chat_caps.supported_temperatures == [1.0]

    def should_disable_tools_for_specific_chat_models(self):
        """
        Given chat models as of 2026-02-04 audit
        When checking tool support
        Then specific models should have tools disabled
        """
        registry = OpenAIModelRegistry()

        # chatgpt-4o-latest does not support tools
        chatgpt_caps = registry.get_model_capabilities("chatgpt-4o-latest")
        assert chatgpt_caps.supports_tools is False
        assert chatgpt_caps.supports_vision is False

        # gpt-4.1-nano does not support tools
        nano_caps = registry.get_model_capabilities("gpt-4.1-nano")
        assert nano_caps.supports_tools is False

        # Search models do not support tools and have no temperature support
        search_caps = registry.get_model_capabilities("gpt-4o-search-preview")
        assert search_caps.supports_tools is False
        assert search_caps.supported_temperatures == []
        assert search_caps.supports_temperature(1.0) is False

        gpt5_search_caps = registry.get_model_capabilities("gpt-5-search-api")
        assert gpt5_search_caps.supports_tools is False
        assert gpt5_search_caps.supported_temperatures == []

        # Audio models do not support tools or streaming
        audio_caps = registry.get_model_capabilities("gpt-4o-audio-preview")
        assert audio_caps.supports_tools is False
        assert audio_caps.supports_streaming is False
