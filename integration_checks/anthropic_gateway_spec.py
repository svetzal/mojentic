import pytest

from integration_checks.models import SimpleResponse, SimpleTool
from mojentic.llm.gateways.anthropic import AnthropicGateway
from mojentic.llm.gateways.models import LLMMessage, MessageRole


# Using fixtures from conftest.py:
# - SimpleResponse: Pydantic model for testing object validation
# - SimpleTool: Tool class for testing tool calls
# - anthropic_api_key: Anthropic API key from environment variables
# - anthropic_gateway: Anthropic gateway instance
# - anthropic_model: Simple Anthropic model for testing


# Fixtures for Anthropic testing
@pytest.fixture
def anthropic_api_key():
    """Get the Anthropic API key from environment variables"""
    import os
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        pytest.skip("ANTHROPIC_API_KEY environment variable not set")
    return api_key


@pytest.fixture
def anthropic_gateway(anthropic_api_key):
    """Create an Anthropic gateway instance"""
    return AnthropicGateway(api_key=anthropic_api_key)


@pytest.fixture
def anthropic_model():
    """Return a simple Anthropic model for testing"""
    return "claude-3-haiku-20240307"


class DescribeAnthropicGatewayIntegration:
    """
    Integration tests for the Anthropic gateway
    """

    class DescribeBasicFunctionality:
        """
        Tests for basic functionality of the Anthropic gateway
        """

        def should_initialize_with_parameters(self, anthropic_api_key):
            """
            Given an API key
            When initializing the Anthropic gateway
            Then it should create a client without errors
            """
            gateway = AnthropicGateway(api_key=anthropic_api_key)

            assert gateway.client is not None

        def should_complete_simple_message(self, anthropic_gateway, anthropic_model):
            """
            Given a simple message
            When completing the message
            Then it should return a non-empty response
            """
            messages = [
                LLMMessage(role=MessageRole.System, content="You are a helpful assistant."),
                LLMMessage(role=MessageRole.User, content="Say hello world")
            ]

            response = anthropic_gateway.complete(model=anthropic_model, messages=messages)

            assert response is not None
            assert response.content is not None
            assert len(response.content) > 0
            assert "hello" in response.content.lower()

        def should_get_available_models(self, anthropic_gateway):
            """
            Given an initialized gateway
            When getting available models
            Then it should return a non-empty list of models
            """
            try:
                models = anthropic_gateway.get_available_models()

                assert models is not None
                assert len(models) > 0
                assert any("claude" in model for model in models)
            except Exception as e:
                pytest.skip(f"Skipping test because Anthropic is not available: {str(e)}")

        def should_calculate_embeddings(self, anthropic_gateway):
            """
            Given a text
            When calculating embeddings
            Then it should raise NotImplementedError
            """
            with pytest.raises(NotImplementedError):
                anthropic_gateway.calculate_embeddings("Hello world")

    class DescribeAdvancedFeatures:
        """
        Tests for advanced features of the Anthropic gateway
        """

        @pytest.mark.skip(reason="Test disabled until functionality is implemented")
        def should_complete_with_object_model(self, anthropic_gateway, anthropic_model):
            """
            Given a message and an object model
            When completing the message with object validation
            Then it should return a validated object
            """
            messages = [
                LLMMessage(role=MessageRole.System, content="You are a helpful assistant."),
                LLMMessage(
                    role=MessageRole.User,
                    content="Answer with a JSON object with fields 'answer' and 'confidence'. Is the sky blue?"
                )
            ]

            response = anthropic_gateway.complete(
                model=anthropic_model,
                messages=messages,
                object_model=SimpleResponse
            )

            assert response is not None
            assert response.object is not None
            assert isinstance(response.object, SimpleResponse)
            assert response.object.answer is not None
            assert response.object.confidence is not None

        @pytest.mark.skip(reason="Test disabled until functionality is implemented")
        def should_complete_with_tool_calls(self, anthropic_gateway, anthropic_model):
            """
            Given a message and a tool
            When completing the message with tool calls
            Then it should return tool calls
            """
            messages = [
                LLMMessage(role=MessageRole.System, content="You are a helpful assistant."),
                LLMMessage(
                    role=MessageRole.User,
                    content="What is 2 + 2? Use the calculator tool."
                )
            ]

            response = anthropic_gateway.complete(
                model=anthropic_model,
                messages=messages,
                tools=[SimpleTool()]
            )

            assert response is not None
            assert response.tool_calls is not None
            assert len(response.tool_calls) > 0
            assert response.tool_calls[0].name == "simple_calculator"
            assert "a" in response.tool_calls[0].arguments
            assert "b" in response.tool_calls[0].arguments

        @pytest.mark.skip(reason="Test disabled until functionality is implemented")
        def should_handle_invalid_model_error(self, anthropic_gateway):
            """
            Given an invalid model name
            When completing a message
            Then it should raise an error
            """
            messages = [
                LLMMessage(role=MessageRole.User, content="Hello")
            ]

            with pytest.raises(Exception):
                anthropic_gateway.complete(model="non-existent-model", messages=messages)
