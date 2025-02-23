from unittest.mock import MagicMock

import pytest
from pydantic import BaseModel

from mojentic.llm.gateways.models import LLMMessage, MessageRole, LLMGatewayResponse, LLMToolCall
from mojentic.llm.llm_broker import LLMBroker


class DummyModel(BaseModel):
    pass


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

        def should_generate_structured_object_from_messages(self, llm_broker, mock_gateway):
            """
            Given messages requiring structured output
            When generating an object
            Then it should return the structured object from LLM
            """
            # Given
            messages = [LLMMessage(role=MessageRole.User, content="Analyze this text.")]
            mock_object = DummyModel()
            mock_gateway.complete.return_value = LLMGatewayResponse(
                content="",
                object=mock_object,
                tool_calls=[]
            )

            # When
            result = llm_broker.generate_object(messages, object_model=MagicMock())

            # Then
            assert result == mock_object
            mock_gateway.complete.assert_called_once()
