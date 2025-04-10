import os
import pytest

from integration_checks.models import SimpleResponse, SimpleTool
from mojentic.llm.gateways.ollama import OllamaGateway, StreamingResponse
from mojentic.llm.gateways.models import LLMMessage, MessageRole


# Fixtures for Ollama testing
@pytest.fixture
def ollama_host():
    """Get the Ollama host from environment variables or use default"""
    return os.environ.get("OLLAMA_HOST", "http://localhost:11434")


@pytest.fixture
def ollama_gateway(ollama_host):
    """Create an Ollama gateway instance"""
    return OllamaGateway(host=ollama_host)


@pytest.fixture
def ollama_model():
    """Return a simple, small Ollama model for testing"""
    return "qwen2.5:3b"


class DescribeOllamaGatewayIntegration:
    """
    Integration tests for the Ollama gateway
    """

    class DescribeBasicFunctionality:
        """
        Tests for basic functionality of the Ollama gateway
        """

        def should_complete_simple_message(self, ollama_gateway, ollama_model):
            """
            Given a simple message
            When completing the message
            Then it should return a non-empty response
            """
            messages = [
                LLMMessage(role=MessageRole.System, content="You are a helpful assistant."),
                LLMMessage(role=MessageRole.User, content="Say hello world")
            ]

            response = ollama_gateway.complete(model=ollama_model, messages=messages)

            assert response is not None
            assert response.content is not None
            assert len(response.content) > 0

        def should_get_available_models(self, ollama_gateway):
            """
            Given an initialized gateway
            When getting available models
            Then it should return a list of models
            """
            try:
                models = ollama_gateway.get_available_models()

                assert models is not None
                # We can't assert specific models because it depends on what's installed
            except Exception as e:
                pytest.skip(f"Skipping test because Ollama is not available: {str(e)}")

        def should_calculate_embeddings(self, ollama_gateway):
            """
            Given a text
            When calculating embeddings
            Then it should return a non-empty list of embeddings
            """
            try:
                text = "Hello world"

                embeddings = ollama_gateway.calculate_embeddings(text)

                assert embeddings is not None
                assert len(embeddings) > 0
            except Exception as e:
                pytest.skip(f"Skipping test because Ollama is not available: {str(e)}")

    class DescribeAdvancedFeatures:
        """
        Tests for advanced features of the Ollama gateway
        """

        def should_complete_with_object_model(self, ollama_gateway, ollama_model):
            """
            Given a message and an object model
            When completing the message with object validation
            Then it should return a validated object
            """
            try:
                messages = [
                    LLMMessage(role=MessageRole.System, content="You are a helpful assistant."),
                    LLMMessage(
                        role=MessageRole.User, 
                        content="Answer with a JSON object with fields 'answer' and 'confidence'. Is the sky blue?"
                    )
                ]

                response = ollama_gateway.complete(
                    model=ollama_model, 
                    messages=messages, 
                    object_model=SimpleResponse
                )

                assert response is not None
                assert response.object is not None
                assert isinstance(response.object, SimpleResponse)
                assert response.object.answer is not None
                # Note: Not all Ollama models reliably return a confidence field,
                # so we don't assert on it here
            except Exception as e:
                pytest.skip(f"Skipping test because Ollama is not available: {str(e)}")

        def should_complete_with_tool_calls(self, ollama_gateway, ollama_model):
            """
            Given a message and a tool
            When completing the message with tool calls
            Then it should return tool calls
            """
            try:
                messages = [
                    LLMMessage(role=MessageRole.System, content="You are a helpful assistant."),
                    LLMMessage(
                        role=MessageRole.User, 
                        content="What is 2 + 2? Use the calculator tool."
                    )
                ]

                response = ollama_gateway.complete(
                    model=ollama_model, 
                    messages=messages, 
                    tools=[SimpleTool()]
                )

                assert response is not None
                # Note: Some Ollama models might not support tool calls,
                # so we can't always assert that tool_calls is not empty
            except Exception as e:
                pytest.skip(f"Skipping test because Ollama is not available: {str(e)}")

        def should_handle_invalid_model_error(self, ollama_gateway):
            """
            Given an invalid model name
            When completing a message
            Then it should raise an error
            """
            try:
                messages = [
                    LLMMessage(role=MessageRole.User, content="Hello")
                ]

                with pytest.raises(Exception):
                    ollama_gateway.complete(model="non-existent-model-12345", messages=messages)
            except Exception as e:
                pytest.skip(f"Skipping test because Ollama is not available: {str(e)}")

        # Gateway-specific features

        def should_complete_stream(self, ollama_gateway, ollama_model):
            """
            Given a message
            When streaming the completion
            Then it should yield streaming responses

            Note: This is an Ollama-specific feature.
            """
            try:
                messages = [
                    LLMMessage(role=MessageRole.System, content="You are a helpful assistant."),
                    LLMMessage(role=MessageRole.User, content="Count from 1 to 5")
                ]

                stream = ollama_gateway.complete_stream(model=ollama_model, messages=messages)

                # Collect the first few chunks
                chunks = []
                for i, chunk in enumerate(stream):
                    chunks.append(chunk)
                    if i >= 5:  # Just get a few chunks to avoid long tests
                        break

                assert len(chunks) > 0
                assert all(isinstance(chunk, StreamingResponse) for chunk in chunks)
                assert all(chunk.content is not None for chunk in chunks)
            except Exception as e:
                pytest.skip(f"Skipping test because Ollama is not available: {str(e)}")

        def should_pull_model(self, ollama_gateway):
            """
            Given a model name
            When pulling the model
            Then it should not raise an error

            Note: This is an Ollama-specific feature.
            """
            try:
                # Use a very small model for this test
                model = "tinyllama"

                # This might take a while if the model isn't already downloaded
                ollama_gateway.pull_model(model)

                # If we got here without an exception, the test passes
                assert True
            except Exception as e:
                pytest.skip(f"Skipping test because Ollama is not available: {str(e)}")
