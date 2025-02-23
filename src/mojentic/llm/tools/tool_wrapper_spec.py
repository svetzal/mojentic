import pytest
from unittest.mock import Mock

from mojentic.llm.tools.tool_wrapper import ToolWrapper
from mojentic.agents.base_llm_agent import BaseLLMAgent
from mojentic.llm.gateways.models import LLMMessage, MessageRole


@pytest.fixture
def mock_llm():
    mock = Mock()
    mock.generate.return_value = "mocked response"
    mock.tools = []
    return mock


@pytest.fixture
def mock_agent(mock_llm):
    agent = Mock(spec=BaseLLMAgent)
    agent.llm = mock_llm
    agent.behaviour = "test behaviour"
    agent.__class__.__name__ = "TestAgent"
    agent.tools = []
    # Mock _create_initial_messages to return an empty list
    agent._create_initial_messages.return_value = []
    return agent


class DescribeToolWrapper:
    """
    Specification for the ToolWrapper class which wraps an agent as a tool for LLM usage.
    """

    class DescribeToolDescriptor:
        """
        Specifications for generating tool descriptors
        """

        def should_generate_proper_function_descriptor(self, mock_agent):
            """
            Given a tool wrapper
            When requesting its descriptor
            Then it should return properly formatted function description
            """
            # Given
            wrapper = ToolWrapper(mock_agent, "testagent", "test behaviour")

            # When
            descriptor = wrapper.descriptor

            # Then
            assert descriptor["type"] == "function"
            assert descriptor["function"]["name"] == "testagent"
            assert descriptor["function"]["description"] == "test behaviour"
            assert "input" in descriptor["function"]["parameters"]["properties"]

    class DescribeToolExecution:
        """
        Specifications for tool execution
        """

        def should_properly_execute_tool_with_input(self, mock_agent):
            """
            Given a tool wrapper
            When running it with input
            Then it should properly delegate to the agent's LLM
            """
            # Given
            wrapper = ToolWrapper(mock_agent, "testagent", "test behaviour")

            # When
            result = wrapper.run("test input")

            # Then
            mock_agent.llm.generate.assert_called_once()
            args, _ = mock_agent.llm.generate.call_args
            messages = args[0]
            assert isinstance(messages[0], LLMMessage)
            assert messages[0].role == MessageRole.User
            assert messages[0].content == "test input"
            assert result == "mocked response"
