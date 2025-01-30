import pytest
from unittest.mock import MagicMock

from pydantic import BaseModel

from mojentic.llm.llm_broker import LLMBroker
from mojentic.llm.gateways.models import LLMMessage, MessageRole, LLMGatewayResponse, LLMToolCall


@pytest.fixture
def mock_gateway(mocker):
    return mocker.MagicMock()

@pytest.fixture
def llm_broker(mock_gateway):
    return LLMBroker(model="test-model", gateway=mock_gateway)

class DummyModel(BaseModel):
    pass

def test_generate_simple_message(llm_broker, mock_gateway):
    test_response_content = "I am fine, thank you!"
    messages = [LLMMessage(role=MessageRole.User, content="Hello, how are you?")]
    mock_gateway.complete.return_value = LLMGatewayResponse(content=test_response_content, object=None, tool_calls=[])

    result = llm_broker.generate(messages)

    assert result == test_response_content
    mock_gateway.complete.assert_called_once()

def test_generate_with_tool_call(llm_broker, mock_gateway, mocker):
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

    result = llm_broker.generate(messages, tools=[mock_tool])

    assert result == "The date is Friday."
    assert mock_gateway.complete.call_count == 2
    mock_tool.run.assert_called_once_with(date="Friday")

def test_generate_object(llm_broker, mock_gateway):
    messages = [LLMMessage(role=MessageRole.User, content="Analyze this text.")]
    mock_object = DummyModel()
    mock_gateway.complete.return_value = LLMGatewayResponse(content="", object=mock_object, tool_calls=[])

    result = llm_broker.generate_object(messages, object_model=MagicMock())

    assert result == mock_object
    mock_gateway.complete.assert_called_once()