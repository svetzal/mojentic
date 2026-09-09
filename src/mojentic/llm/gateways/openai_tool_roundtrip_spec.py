"""
Parity-protective spec for the OpenAI tool-calling round-trip at the adapter boundary.

Uses the canonical get_weather fixtures shared across mojentic-py, mojentic-ts,
mojentic-ex, and mojentic-ru. The fixture JSON files in
fixtures/openai_tool_roundtrip/ must remain byte-identical across all four ports.

Verifies that:
- The first LLM call's tools list includes a function named get_weather
- The get_weather tool is invoked with location == "Paris"
- The second LLM call's messages contain the correct assistant tool_call message
  (arguments as a JSON object, not a string-that-parses-to-a-string) and a tool-role
  message with the correct tool_call_id and JSON content
- The final returned text matches the second fixture response
"""

import json
import pytest
from pathlib import Path
from unittest.mock import MagicMock

from mojentic.llm.gateways.openai import OpenAIGateway
from mojentic.llm.gateways.models import LLMMessage, MessageRole
from mojentic.llm.llm_broker import LLMBroker
from mojentic.llm.tools.llm_tool import LLMTool

_FIXTURES_DIR = Path(__file__).parent / "fixtures" / "openai_tool_roundtrip"


def _load_fixture(name):
    with open(_FIXTURES_DIR / name) as f:
        return json.load(f)


class GetWeatherTool(LLMTool):
    """Real LLMTool that returns the canonical tool-result fixture."""

    def run(self, location: str):
        return _load_fixture("tool-result.json")

    @property
    def descriptor(self):
        return {
            "type": "function",
            "function": {
                "name": "get_weather",
                "description": "Get the current weather for a location",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "location": {"type": "string"},
                    },
                    "required": ["location"],
                },
            },
        }


@pytest.fixture
def mock_openai_client(mocker):
    """Build a mock OpenAI client backed by the canonical round-trip fixtures."""
    fixture1 = _load_fixture("response-1-tool-call.json")
    fixture2 = _load_fixture("response-2-final.json")

    from openai.types.chat import ChatCompletion
    resp1 = ChatCompletion.model_validate(fixture1)
    resp2 = ChatCompletion.model_validate(fixture2)

    mock_client = MagicMock()
    mock_client.chat.completions.create.side_effect = [resp1, resp2]

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
    return GetWeatherTool()


class DescribeOpenAIToolCallingRoundTrip:

    def should_include_get_weather_in_first_request_tools(
            self, broker, tool, mock_openai_client):
        messages = [LLMMessage(role=MessageRole.User, content="What's the weather in Paris?")]

        broker.generate(messages, tools=[tool])

        first_call_kwargs = mock_openai_client.chat.completions.create.call_args_list[0][1]
        tool_names = [t["function"]["name"] for t in first_call_kwargs["tools"]]
        assert "get_weather" in tool_names

    def should_invoke_get_weather_tool_with_paris(self, broker, tool, mock_openai_client, mocker):
        spy = mocker.spy(tool, "run")
        messages = [LLMMessage(role=MessageRole.User, content="What's the weather in Paris?")]

        broker.generate(messages, tools=[tool])

        spy.assert_called_once_with(location="Paris")

    def should_include_correct_assistant_tool_call_in_second_request(
            self, broker, tool, mock_openai_client):
        messages = [LLMMessage(role=MessageRole.User, content="What's the weather in Paris?")]

        broker.generate(messages, tools=[tool])

        second_call_kwargs = mock_openai_client.chat.completions.create.call_args_list[1][1]
        second_messages = second_call_kwargs["messages"]

        # Must contain the original user message
        user_msgs = [m for m in second_messages if m.get("role") == "user"]
        assert any(m.get("content") == "What's the weather in Paris?" for m in user_msgs)

        # Must contain an assistant message with a tool_call whose arguments parse to a dict
        assistant_msgs = [m for m in second_messages if m.get("role") == "assistant"]
        assert len(assistant_msgs) >= 1
        tool_call_msgs = [m for m in assistant_msgs if "tool_calls" in m]
        assert len(tool_call_msgs) >= 1
        args_str = tool_call_msgs[0]["tool_calls"][0]["function"]["arguments"]
        parsed_args = json.loads(args_str)
        assert isinstance(parsed_args, dict), "arguments must parse to a dict, not a nested string"
        assert parsed_args == {"location": "Paris"}

    def should_include_correct_tool_role_message_in_second_request(
            self, broker, tool, mock_openai_client):
        messages = [LLMMessage(role=MessageRole.User, content="What's the weather in Paris?")]

        broker.generate(messages, tools=[tool])

        second_call_kwargs = mock_openai_client.chat.completions.create.call_args_list[1][1]
        second_messages = second_call_kwargs["messages"]

        tool_msgs = [m for m in second_messages if m.get("role") == "tool"]
        assert len(tool_msgs) == 1
        tool_msg = tool_msgs[0]
        assert tool_msg.get("tool_call_id") == "call_fixture_get_weather"
        assert "tool_calls" not in tool_msg, "tool-role message must not contain tool_calls array"
        content_parsed = json.loads(tool_msg["content"])
        assert content_parsed == {"temperature_c": 22, "conditions": "sunny"}

    def should_return_final_text_from_second_response(
            self, broker, tool, mock_openai_client):
        messages = [LLMMessage(role=MessageRole.User, content="What's the weather in Paris?")]

        result = broker.generate(messages, tools=[tool])

        assert result == "It's currently 22°C and sunny in Paris."


def should_preserve_json_argument_types_and_provider_metadata(mocker):
    from openai.types.chat import ChatCompletion
    fixture = _load_fixture("response-1-tool-call.json")
    arguments = {"count": 2, "enabled": True, "items": ["one"], "filter": {"kind": None}}
    fixture["choices"][0]["message"]["tool_calls"][0]["function"]["arguments"] = json.dumps(arguments)
    fixture["usage"] = {"prompt_tokens": 10, "completion_tokens": 4, "total_tokens": 14}
    client = MagicMock()
    client.chat.completions.create.return_value = ChatCompletion.model_validate(fixture)
    mocker.patch('mojentic.llm.gateways.openai.OpenAI', return_value=client)
    broker = LLMBroker(model="configured-model", gateway=OpenAIGateway(api_key="test-key"))
    response = broker.generate_response([LLMMessage(role=MessageRole.User, content="hi")])
    assert response.tool_calls[0].arguments == arguments
    assert response.usage["prompt_tokens"] == 10
    assert response.model == fixture["model"]
    assert response.finish_reason == "tool_calls"
