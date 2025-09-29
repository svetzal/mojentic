import pytest
from unittest.mock import MagicMock

from mojentic.llm.gateways.openai import OpenAIGateway
from mojentic.llm.gateways.openai_model_registry import get_model_registry
from mojentic.llm.gateways.models import LLMMessage, MessageRole, LLMGatewayResponse


@pytest.fixture
def mock_openai_client(mocker):
    """Mock the OpenAI client."""
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = MagicMock()
    mock_client.chat.completions.create.return_value.choices = [MagicMock()]
    mock_client.chat.completions.create.return_value.choices[0].message.content = "Test response"
    mock_client.chat.completions.create.return_value.choices[0].message.tool_calls = None
    return mock_client


@pytest.fixture
def openai_gateway(mocker, mock_openai_client):
    """Create an OpenAI gateway with mocked client."""
    mocker.patch('mojentic.llm.gateways.openai.OpenAI', return_value=mock_openai_client)
    return OpenAIGateway(api_key="test_key")


class DescribeOpenAIGatewayTemperatureHandling:
    """
    Specification for OpenAI gateway temperature parameter handling.
    """

    class DescribeGPT5TemperatureRestrictions:
        """
        Specifications for GPT-5 model temperature restrictions.
        """

        def should_automatically_adjust_unsupported_temperature_for_gpt5(self, openai_gateway, mock_openai_client):
            """
            Given a GPT-5 model that only supports temperature=1.0
            When calling complete with temperature=0.1 (unsupported)
            Then it should automatically adjust to temperature=1.0
            """
            messages = [LLMMessage(role=MessageRole.User, content="Test message")]

            openai_gateway.complete(
                model="gpt-5",
                messages=messages,
                temperature=0.1
            )

            # Verify the API was called with temperature=1.0, not 0.1
            call_args = mock_openai_client.chat.completions.create.call_args
            assert call_args[1]['temperature'] == 1.0

        def should_preserve_supported_temperature_for_gpt5(self, openai_gateway, mock_openai_client):
            """
            Given a GPT-5 model that supports temperature=1.0
            When calling complete with temperature=1.0 (supported)
            Then it should preserve the temperature value
            """
            messages = [LLMMessage(role=MessageRole.User, content="Test message")]

            openai_gateway.complete(
                model="gpt-5",
                messages=messages,
                temperature=1.0
            )

            # Verify the API was called with temperature=1.0
            call_args = mock_openai_client.chat.completions.create.call_args
            assert call_args[1]['temperature'] == 1.0

        def should_preserve_any_temperature_for_gpt4o(self, openai_gateway, mock_openai_client):
            """
            Given a GPT-4o model that supports all temperatures
            When calling complete with temperature=0.1
            Then it should preserve the original temperature value
            """
            messages = [LLMMessage(role=MessageRole.User, content="Test message")]

            openai_gateway.complete(
                model="gpt-4o",
                messages=messages,
                temperature=0.1
            )

            # Verify the API was called with temperature=0.1
            call_args = mock_openai_client.chat.completions.create.call_args
            assert call_args[1]['temperature'] == 0.1

        def should_automatically_adjust_unsupported_temperature_for_o1_mini(self, openai_gateway, mock_openai_client):
            """
            Given an o1-mini model that only supports temperature=1.0
            When calling complete with temperature=0.1 (unsupported)
            Then it should automatically adjust to temperature=1.0
            """
            messages = [LLMMessage(role=MessageRole.User, content="Test message")]

            openai_gateway.complete(
                model="o1-mini",
                messages=messages,
                temperature=0.1
            )

            # Verify the API was called with temperature=1.0, not 0.1
            call_args = mock_openai_client.chat.completions.create.call_args
            assert call_args[1]['temperature'] == 1.0

        def should_automatically_adjust_unsupported_temperature_for_o4_mini(self, openai_gateway, mock_openai_client):
            """
            Given an o4-mini model that only supports temperature=1.0
            When calling complete with temperature=0.1 (unsupported)
            Then it should automatically adjust to temperature=1.0
            """
            messages = [LLMMessage(role=MessageRole.User, content="Test message")]

            openai_gateway.complete(
                model="o4-mini",
                messages=messages,
                temperature=0.1
            )

            # Verify the API was called with temperature=1.0, not 0.1
            call_args = mock_openai_client.chat.completions.create.call_args
            assert call_args[1]['temperature'] == 1.0

        def should_remove_temperature_parameter_for_o3_mini(self, openai_gateway, mock_openai_client):
            """
            Given an o3-mini model that doesn't support temperature parameter at all
            When calling complete with temperature=0.1
            Then it should remove the temperature parameter entirely
            """
            messages = [LLMMessage(role=MessageRole.User, content="Test message")]

            openai_gateway.complete(
                model="o3-mini",
                messages=messages,
                temperature=0.1
            )

            # Verify the API was called without temperature parameter
            call_args = mock_openai_client.chat.completions.create.call_args
            assert 'temperature' not in call_args[1]


class DescribeModelCapabilitiesTemperatureRestrictions:
    """
    Specification for model capabilities temperature restriction checks.
    """

    def should_identify_gpt5_temperature_restrictions(self):
        """
        Given the model registry
        When checking GPT-5 model capabilities
        Then it should indicate temperature=1.0 is supported and temperature=0.1 is not
        """
        registry = get_model_registry()
        capabilities = registry.get_model_capabilities("gpt-5")

        assert capabilities.supports_temperature(1.0) is True
        assert capabilities.supports_temperature(0.1) is False
        assert capabilities.supported_temperatures == [1.0]

    def should_allow_all_temperatures_for_gpt4o(self):
        """
        Given the model registry
        When checking GPT-4o model capabilities
        Then it should indicate all temperature values are supported
        """
        registry = get_model_registry()
        capabilities = registry.get_model_capabilities("gpt-4o")

        assert capabilities.supports_temperature(1.0) is True
        assert capabilities.supports_temperature(0.1) is True
        assert capabilities.supports_temperature(0.7) is True
        assert capabilities.supported_temperatures is None

    def should_identify_all_gpt5_variants_temperature_restrictions(self):
        """
        Given the model registry
        When checking all GPT-5 variant models
        Then they should all have temperature restrictions to 1.0 only
        """
        registry = get_model_registry()
        gpt5_models = [
            "gpt-5",
            "gpt-5-2025-08-07",
            "gpt-5-chat-latest",
            "gpt-5-codex",
            "gpt-5-mini",
            "gpt-5-mini-2025-08-07",
            "gpt-5-nano",
            "gpt-5-nano-2025-08-07"
        ]

        for model in gpt5_models:
            capabilities = registry.get_model_capabilities(model)
            assert capabilities.supports_temperature(1.0) is True
            assert capabilities.supports_temperature(0.1) is False
            assert capabilities.supported_temperatures == [1.0]

    def should_identify_o1_series_temperature_restrictions(self):
        """
        Given the model registry
        When checking o1 series models
        Then they should have temperature restrictions to 1.0 only
        """
        registry = get_model_registry()
        o1_models = ["o1", "o1-mini", "o1-pro", "o1-2024-12-17"]

        for model in o1_models:
            capabilities = registry.get_model_capabilities(model)
            assert capabilities.supports_temperature(1.0) is True
            assert capabilities.supports_temperature(0.1) is False
            assert capabilities.supported_temperatures == [1.0]

    def should_identify_o3_series_no_temperature_support(self):
        """
        Given the model registry
        When checking o3 series models
        Then they should not support temperature parameter at all
        """
        registry = get_model_registry()
        o3_models = ["o3", "o3-mini", "o3-pro", "o3-deep-research"]

        for model in o3_models:
            capabilities = registry.get_model_capabilities(model)
            assert capabilities.supports_temperature(1.0) is False
            assert capabilities.supports_temperature(0.1) is False
            assert capabilities.supported_temperatures == []

    def should_identify_o4_series_temperature_restrictions(self):
        """
        Given the model registry
        When checking o4 series models
        Then they should have temperature restrictions to 1.0 only
        """
        registry = get_model_registry()
        o4_models = ["o4-mini", "o4-mini-2025-04-16", "o4-mini-deep-research"]

        for model in o4_models:
            capabilities = registry.get_model_capabilities(model)
            assert capabilities.supports_temperature(1.0) is True
            assert capabilities.supports_temperature(0.1) is False
            assert capabilities.supported_temperatures == [1.0]