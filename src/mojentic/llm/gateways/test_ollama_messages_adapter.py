import json

from mojentic.llm.gateways.models import LLMMessage, MessageRole, LLMToolCall
from mojentic.llm.gateways.ollama_messages_adapter import adapt_messages_to_ollama


def test_simple_system_message():
    messages = [LLMMessage(role=MessageRole.System, content="This is a system message")]

    adapted_messages = adapt_messages_to_ollama(messages)

    assert adapted_messages == [
        {
            'role': 'system',
            'content': 'This is a system message'
        }
    ]


def test_simple_user_message():
    messages = [LLMMessage(role=MessageRole.User, content="Hello, how are you?")]

    adapted_messages = adapt_messages_to_ollama(messages)

    assert adapted_messages == [
        {
            'role': 'user',
            'content': 'Hello, how are you?'
        }
    ]


def test_simple_assistant_message():
    messages = [LLMMessage(role=MessageRole.Assistant, content="I am fine, thank you!")]

    adapted_messages = adapt_messages_to_ollama(messages)

    assert adapted_messages == [
        {
            'role': 'assistant',
            'content': 'I am fine, thank you!'
        }
    ]


def test_assistant_message_with_tool_call():
    tool_name = "tool_name"
    tool_arguments = {"argument": "value"}
    messages = [LLMMessage(
        role=MessageRole.Assistant,
        content="I am fine, thank you!",
        tool_calls=[LLMToolCall(
            name=tool_name,
            arguments=tool_arguments
        )]
    )]

    adapted_messages = adapt_messages_to_ollama(messages)

    assert adapted_messages == [
        {
            'role': 'assistant',
            'content': 'I am fine, thank you!',
            'tool_calls': [
                {
                    'type': 'function',
                    'function': {
                        'name': tool_name,
                        'arguments': tool_arguments
                    }
                }
            ]
        }
    ]


def test_tool_response_message():
    messages = [LLMMessage(role=MessageRole.Tool, content=json.dumps({"date": "Friday"}))]

    adapted_messages = adapt_messages_to_ollama(messages)

    assert adapted_messages == [
        {
            'role': 'tool',
            'content': '{"date": "Friday"}'  # must be a string
        }
    ]
