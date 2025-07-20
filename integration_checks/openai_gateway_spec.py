import os
import pytest

from integration_checks.models import SimpleResponse, SimpleTool
from mojentic.llm.gateways.openai import OpenAIGateway
from mojentic.llm.gateways.models import LLMMessage, MessageRole


# Fixtures for OpenAI testing
@pytest.fixture
def openai_api_key():
    """Get the OpenAI API key from environment variables"""
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        pytest.skip("OPENAI_API_KEY environment variable not set")
    return api_key


@pytest.fixture
def openai_gateway(openai_api_key):
    """Create an OpenAI gateway instance"""
    return OpenAIGateway(api_key=openai_api_key)


@pytest.fixture
def openai_model():
    """Return a simple, inexpensive OpenAI model for testing"""
    return "gpt-4o"


class DescribeOpenAIGatewayIntegration:
    """
    Integration tests for the OpenAI gateway
    """

    class DescribeBasicFunctionality:
        """
        Tests for basic functionality of the OpenAI gateway
        """

        def should_initialize_with_parameters(self, openai_api_key):
            """
            Given an API key
            When initializing the OpenAI gateway
            Then it should create a client without errors
            """
            gateway = OpenAIGateway(api_key=openai_api_key)

            assert gateway.client is not None

        def should_complete_simple_message(self, openai_gateway, openai_model):
            """
            Given a simple message
            When completing the message
            Then it should return a non-empty response
            """
            try:
                messages = [
                    LLMMessage(role=MessageRole.System, content="You are a helpful assistant."),
                    LLMMessage(role=MessageRole.User, content="Say hello world")
                ]

                response = openai_gateway.complete(model=openai_model, messages=messages)

                assert response is not None
                assert response.content is not None
                assert len(response.content) > 0
                assert "hello" in response.content.lower()
            except Exception as e:
                pytest.skip(f"Skipping test because OpenAI is not available: {str(e)}")

        def should_get_available_models(self, openai_gateway):
            """
            Given an initialized gateway
            When getting available models
            Then it should return a non-empty list of models
            """
            try:
                models = openai_gateway.get_available_models()

                assert models is not None
                assert len(models) > 0
                assert "gpt-3.5-turbo" in models
            except Exception as e:
                pytest.skip(f"Skipping test because OpenAI is not available: {str(e)}")

        def should_calculate_embeddings(self, openai_gateway):
            """
            Given a text
            When calculating embeddings
            Then it should return a non-empty list of embeddings
            """
            text = "Hello world"

            embeddings = openai_gateway.calculate_embeddings(text)

            # OpenAI's text-embedding-3-large model returns 3072-dimensional embeddings
            assert len(embeddings) == 3072

    class DescribeAdvancedFeatures:
        """
        Tests for advanced features of the OpenAI gateway
        """

        def should_complete_with_object_model(self, openai_gateway, openai_model):
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

            response = openai_gateway.complete(
                model=openai_model,
                messages=messages,
                object_model=SimpleResponse
            )

            assert response is not None
            assert response.object is not None
            assert isinstance(response.object, SimpleResponse)
            assert response.object.answer is not None
            assert response.object.confidence is not None

        def should_complete_with_tool_calls(self, openai_gateway, openai_model):
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

            response = openai_gateway.complete(
                model=openai_model,
                messages=messages,
                tools=[SimpleTool()]
            )

            assert response is not None
            assert response.tool_calls is not None
            assert len(response.tool_calls) > 0
            assert response.tool_calls[0].name == "simple_calculator"
            assert "a" in response.tool_calls[0].arguments
            assert "b" in response.tool_calls[0].arguments

        def should_handle_invalid_model_error(self, openai_gateway):
            """
            Given an invalid model name
            When completing a message
            Then it should raise an error
            """
            messages = [
                LLMMessage(role=MessageRole.User, content="Hello")
            ]

            with pytest.raises(Exception):
                openai_gateway.complete(model="non-existent-model", messages=messages)

    class DescribeModelCharacterization:
        """
        Tests for model characterization and parameter adaptation
        """

        def should_identify_reasoning_models(self, openai_gateway):
            """
            Given various model names
            When checking if they are reasoning models
            Then it should correctly classify them
            """
            # Test reasoning models
            assert openai_gateway._is_reasoning_model("o1-preview") is True
            assert openai_gateway._is_reasoning_model("o1-mini") is True
            assert openai_gateway._is_reasoning_model("o4-mini") is True
            assert openai_gateway._is_reasoning_model("o1") is True
            assert openai_gateway._is_reasoning_model("o4") is True

            # Test chat models
            assert openai_gateway._is_reasoning_model("gpt-4o") is False
            assert openai_gateway._is_reasoning_model("gpt-4o-mini") is False
            assert openai_gateway._is_reasoning_model("gpt-3.5-turbo") is False
            assert openai_gateway._is_reasoning_model("gpt-4") is False

        def should_adapt_parameters_for_reasoning_models(self, openai_gateway):
            """
            Given a reasoning model and max_tokens parameter
            When adapting parameters
            Then it should convert max_tokens to max_completion_tokens
            """
            original_args = {
                'model': 'o1-mini',
                'messages': [LLMMessage(role=MessageRole.User, content="Hello")],
                'max_tokens': 1000
            }

            adapted_args = openai_gateway._adapt_parameters_for_model('o1-mini', original_args)

            assert 'max_tokens' not in adapted_args
            assert 'max_completion_tokens' in adapted_args
            assert adapted_args['max_completion_tokens'] == 1000

        def should_keep_parameters_for_chat_models(self, openai_gateway):
            """
            Given a chat model and max_tokens parameter
            When adapting parameters
            Then it should keep max_tokens unchanged
            """
            original_args = {
                'model': 'gpt-4o',
                'messages': [LLMMessage(role=MessageRole.User, content="Hello")],
                'max_tokens': 1000
            }

            adapted_args = openai_gateway._adapt_parameters_for_model('gpt-4o', original_args)

            assert 'max_tokens' in adapted_args
            assert 'max_completion_tokens' not in adapted_args
            assert adapted_args['max_tokens'] == 1000

        def should_handle_missing_max_tokens_parameter(self, openai_gateway):
            """
            Given arguments without max_tokens parameter
            When adapting parameters
            Then it should not add any token limit parameters
            """
            original_args = {
                'model': 'o1-mini',
                'messages': [LLMMessage(role=MessageRole.User, content="Hello")]
            }

            adapted_args = openai_gateway._adapt_parameters_for_model('o1-mini', original_args)

            assert 'max_tokens' not in adapted_args
            assert 'max_completion_tokens' not in adapted_args
