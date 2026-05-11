"""
Parity-protective spec for the OpenAI tool-calling round-trip at the adapter boundary.

Verifies that:
- The broker correctly dispatches tool calls from the first LLM response
- The tool is invoked with the expected arguments
- The second LLM call's messages include the assistant tool_call message and the tool role message
- The final text from the second response is returned correctly
"""

import json
import pytest
from unittest.mock import MagicMock

from mojentic.llm.gateways.openai import OpenAIGateway
from mojentic.llm.gateways.models import LLMMessage, MessageRole
from mojentic.llm.llm_broker import LLMBroker
from mojentic.llm.tools.llm_tool import LLMTool


class AddTool(LLMTool):
    """A minimal real LLMTool subclass that adds two numbers."""

    def run(self, a: str, b: str):
        return {"result": str(int(a) + int(b))}

    @property
    def descriptor(self):
        return {
            "type": "function",
            "function": {
                "name": "add",
                "description": "Adds two numbers",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "a": {"type": "string"},
                        "b": {"type": "string"},
                    },
                    "required": ["a", "b"],
                },
            },
        }


@pytest.fixture
def mock_openai_client(mocker):
    """Build a mock OpenAI client with two-response side-effect."""
    tool_call_mock = MagicMock()
    tool_call_mock.id = "call_abc123"
    tool_call_mock.function.name = "add"
    tool_call_mock.function.arguments = json.dumps({"a": "20", "b": "22"})

    first_response = MagicMock()
    first_response.choices = [MagicMock()]
    first_response.choices[0].message.content = None
    first_response.choices[0].message.tool_calls = [tool_call_mock]

    second_response = MagicMock()
    second_response.choices = [MagicMock()]
    second_response.choices[0].message.content = "The answer is 42"
    second_response.choices[0].message.tool_calls = None

    mock_client = MagicMock()
    mock_client.chat.completions.create.side_effect = [first_response, second_response]

    mocker.patch('mojentic.llm.gateways.openai.OpenAI', return_value=mock_client)
    return mock_client


@pytest.fixture
def openai_gateway(mock_openai_client):
    return OpenAIGateway(api_key="test-key")


@pytest.fixture
def broker(openai_gateway):
    return LLMBroker(model="gpt-4o", gateway=openai_gateway)


@pytest.fixture
def tool():
    return AddTool()


class DescribeOpenAIToolCallingRoundTrip:

    def should_return_final_text_after_tool_invocation(
            self, broker, tool, mock_openai_client):
        messages = [LLMMessage(role=MessageRole.User, content="What is 20 + 22?")]

        result = broker.generate(messages, tools=[tool])

        assert result == "The answer is 42"

    def should_invoke_tool_exactly_once(self, broker, tool, mock_openai_client, mocker):
        spy = mocker.spy(tool, "run")
        messages = [LLMMessage(role=MessageRole.User, content="What is 20 + 22?")]

        broker.generate(messages, tools=[tool])

        spy.assert_called_once_with(a="20", b="22")

    def should_include_assistant_tool_call_message_in_second_request(
            self, broker, tool, mock_openai_client):
        messages = [LLMMessage(role=MessageRole.User, content="What is 20 + 22?")]

        broker.generate(messages, tools=[tool])

        second_call_args = mock_openai_client.chat.completions.create.call_args_list[1]
        second_messages = second_call_args[1]['messages']

        assistant_msgs = [m for m in second_messages if m.get('role') == 'assistant']
        assert len(assistant_msgs) >= 1
        assert any('tool_calls' in m for m in assistant_msgs)

    def should_include_tool_role_message_in_second_request(
            self, broker, tool, mock_openai_client):
        messages = [LLMMessage(role=MessageRole.User, content="What is 20 + 22?")]

        broker.generate(messages, tools=[tool])

        second_call_args = mock_openai_client.chat.completions.create.call_args_list[1]
        second_messages = second_call_args[1]['messages']

        tool_msgs = [m for m in second_messages if m.get('role') == 'tool']
        assert len(tool_msgs) == 1
        assert tool_msgs[0].get('tool_call_id') == "call_abc123"
