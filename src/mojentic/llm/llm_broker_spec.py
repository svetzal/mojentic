from unittest.mock import MagicMock

import pytest
from pydantic import BaseModel

from mojentic.llm.gateways.models import LLMMessage, MessageRole, LLMGatewayResponse, LLMToolCall
from mojentic.llm.llm_broker import LLMBroker


class SimpleModel(BaseModel):
    text: str
    number: int

class NestedModel(BaseModel):
    title: str
    details: SimpleModel

class ComplexModel(BaseModel):
    name: str
    items: list[SimpleModel]
    metadata: dict[str, str]


@pytest.fixture
def mock_gateway(mocker):
    return mocker.MagicMock()


@pytest.fixture
def llm_broker(mock_gateway):
    return LLMBroker(model="test-model", gateway=mock_gateway)


class DescribeLLMBroker:
    """
    Specification for the LLMBroker class which handles interactions with Language Learning Models.
    """

    class DescribeMessageGeneration:
        """
        Specifications for generating messages through the LLM broker
        """

        def should_generate_simple_response_for_user_message(self, llm_broker, mock_gateway):
            """
            Given a simple user message
            When generating a response
            Then it should return the LLM's response content
            """
            # Given
            test_response_content = "I am fine, thank you!"
            messages = [LLMMessage(role=MessageRole.User, content="Hello, how are you?")]
            mock_gateway.complete.return_value = LLMGatewayResponse(
                content=test_response_content,
                object=None,
                tool_calls=[]
            )

            # When
            result = llm_broker.generate(messages)

            # Then
            assert result == test_response_content
            mock_gateway.complete.assert_called_once()

        def should_handle_tool_calls_during_generation(self, llm_broker, mock_gateway, mocker):
            """
            Given a message that requires tool usage
            When generating a response
            Then it should properly handle tool calls and return final response
            """
            # Given
            messages = [LLMMessage(role=MessageRole.User, content="What is the date on Friday?")]
            tool_call = mocker.create_autospec(LLMToolCall, instance=True)
            tool_call.name = "resolve_date"
            tool_call.arguments = {"date": "Friday"}

            mock_gateway.complete.side_effect = [
                LLMGatewayResponse(content="", object=None, tool_calls=[tool_call]),
                LLMGatewayResponse(content="The date is Friday.", object=None, tool_calls=[])
            ]

            mock_tool = mocker.MagicMock()
            mock_tool.matches.return_value = True
            mock_tool.run.return_value = {"resolved_date": "Friday"}

            # When
            result = llm_broker.generate(messages, tools=[mock_tool])

            # Then
            assert result == "The date is Friday."
            assert mock_gateway.complete.call_count == 2
            mock_tool.run.assert_called_once_with(date="Friday")

    class DescribeObjectGeneration:
        """
        Specifications for generating structured objects through the LLM broker
        """

        def should_generate_simple_model(self, llm_broker, mock_gateway):
            """
            Given messages requiring a simple structured output
            When generating an object with SimpleModel
            Then it should return the validated SimpleModel object
            """
            # Given
            messages = [LLMMessage(role=MessageRole.User, content="Generate a simple object")]
            mock_object = SimpleModel(text="test", number=42)
            mock_gateway.complete.return_value = LLMGatewayResponse(
                content='{"text": "test", "number": 42}',
                object=mock_object,
                tool_calls=[]
            )

            # When
            result = llm_broker.generate_object(messages, object_model=SimpleModel)

            # Then
            assert isinstance(result, SimpleModel)
            assert result.text == "test"
            assert result.number == 42
            mock_gateway.complete.assert_called_once()

        def should_generate_nested_model(self, llm_broker, mock_gateway):
            """
            Given messages requiring a nested structured output
            When generating an object with NestedModel
            Then it should return the validated NestedModel object
            """
            # Given
            messages = [LLMMessage(role=MessageRole.User, content="Generate a nested object")]
            mock_object = NestedModel(
                title="main",
                details=SimpleModel(text="nested", number=123)
            )
            mock_gateway.complete.return_value = LLMGatewayResponse(
                content='{"title": "main", "details": {"text": "nested", "number": 123}}',
                object=mock_object,
                tool_calls=[]
            )

            # When
            result = llm_broker.generate_object(messages, object_model=NestedModel)

            # Then
            assert isinstance(result, NestedModel)
            assert result.title == "main"
            assert isinstance(result.details, SimpleModel)
            assert result.details.text == "nested"
            assert result.details.number == 123
            mock_gateway.complete.assert_called_once()

        def should_generate_complex_model(self, llm_broker, mock_gateway):
            """
            Given messages requiring a complex structured output
            When generating an object with ComplexModel
            Then it should return the validated ComplexModel object
            """
            # Given
            messages = [LLMMessage(role=MessageRole.User, content="Generate a complex object")]
            mock_object = ComplexModel(
                name="test",
                items=[
                    SimpleModel(text="item1", number=1),
                    SimpleModel(text="item2", number=2)
                ],
                metadata={"key1": "value1", "key2": "value2"}
            )
            mock_gateway.complete.return_value = LLMGatewayResponse(
                content='{"name": "test", "items": [{"text": "item1", "number": 1}, {"text": "item2", "number": 2}], "metadata": {"key1": "value1", "key2": "value2"}}',
                object=mock_object,
                tool_calls=[]
            )

            # When
            result = llm_broker.generate_object(messages, object_model=ComplexModel)

            # Then
            assert isinstance(result, ComplexModel)
            assert result.name == "test"
            assert len(result.items) == 2
            assert all(isinstance(item, SimpleModel) for item in result.items)
            assert result.items[0].text == "item1"
            assert result.items[1].number == 2
            assert result.metadata == {"key1": "value1", "key2": "value2"}
            mock_gateway.complete.assert_called_once()
