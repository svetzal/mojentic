import json

import pytest

from mojentic.llm.gateways.models import LLMMessage, MessageRole, LLMToolCall
from mojentic.llm.gateways.openai_messages_adapter import adapt_messages_to_openai


def test_simple_system_message():
    messages = [LLMMessage(role=MessageRole.System, content="This is a system message")]

    adapted_messages = adapt_messages_to_openai(messages)

    assert adapted_messages == [
        {
            'role': 'system',
            'content': 'This is a system message'
        }
    ]


def test_simple_user_message():
    messages = [LLMMessage(role=MessageRole.User, content="Hello, how are you?")]

    adapted_messages = adapt_messages_to_openai(messages)

    assert adapted_messages == [
        {
            'role': 'user',
            'content': 'Hello, how are you?'
        }
    ]


def test_simple_assistant_message():
    messages = [LLMMessage(role=MessageRole.Assistant, content="I am fine, thank you!")]

    adapted_messages = adapt_messages_to_openai(messages)

    assert adapted_messages == [
        {
            'role': 'assistant',
            'content': 'I am fine, thank you!'
        }
    ]


@pytest.fixture
def tool_name():
    return "tool_name"


@pytest.fixture
def tool_arguments():
    return {"argument": "value"}


@pytest.fixture
def tool_call(tool_name, tool_arguments):
    return LLMToolCall(
        id="abc",
        name=tool_name,
        arguments=tool_arguments
    )


def test_assistant_message_with_tool_call(tool_name, tool_arguments):
    messages = [LLMMessage(
        role=MessageRole.Assistant,
        content="I am fine, thank you!",
        tool_calls=[LLMToolCall(
            id="abc",
            name=tool_name,
            arguments=tool_arguments
        )]
    )]

    adapted_messages = adapt_messages_to_openai(messages)

    assert adapted_messages == [
        {
            'role': 'assistant',
            'content': 'I am fine, thank you!',
            'tool_calls': [
                {
                    'id': 'abc',
                    'type': 'function',
                    'function': {
                        'name': tool_name,
                        'arguments': json.dumps(tool_arguments)
                    }
                }
            ]
        }
    ]


def test_tool_response_message(tool_call):
    messages = [LLMMessage(role=MessageRole.Tool, content='{"date": "Friday"}', tool_calls=[tool_call])]

    adapted_messages = adapt_messages_to_openai(messages)

    assert adapted_messages == [
        {
            'role': 'tool',
            'content': '{"date": "Friday"}',
            'tool_call_id': tool_call.id
        }
    ]
