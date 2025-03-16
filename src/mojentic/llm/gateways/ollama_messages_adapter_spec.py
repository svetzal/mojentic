import json
import pytest

from mojentic.llm.gateways.models import LLMMessage, MessageRole, LLMToolCall
from mojentic.llm.gateways.ollama_messages_adapter import adapt_messages_to_ollama


@pytest.fixture
def tool_name():
    return "tool_name"


@pytest.fixture
def tool_arguments():
    return {"argument": "value"}


class DescribeOllamaMessagesAdapter:
    """
    Specification for the Ollama messages adapter which handles conversion of messages to Ollama format.
    """

    class DescribeSimpleMessages:
        """
        Specifications for adapting simple messages without tool calls
        """

        def should_adapt_system_message(self):
            """
            Given a system message
            When adapting to Ollama format
            Then it should convert to the correct format
            """
            messages = [LLMMessage(role=MessageRole.System, content="This is a system message")]

            adapted_messages = adapt_messages_to_ollama(messages)

            assert adapted_messages == [
                {
                    'role': 'system',
                    'content': 'This is a system message'
                }
            ]

        def should_adapt_user_message(self):
            """
            Given a user message
            When adapting to Ollama format
            Then it should convert to the correct format
            """
            messages = [LLMMessage(role=MessageRole.User, content="Hello, how are you?")]

            adapted_messages = adapt_messages_to_ollama(messages)

            assert adapted_messages == [
                {
                    'role': 'user',
                    'content': 'Hello, how are you?'
                }
            ]

        def should_adapt_user_message_with_image_paths(self):
            """
            Given a user message with image paths
            When adapting to Ollama format
            Then it should convert to the correct format with images key
            """
            image_paths = ["/path/to/image1.jpg", "/path/to/image2.jpg"]
            messages = [LLMMessage(role=MessageRole.User, content="What's in these images?", image_paths=image_paths)]

            adapted_messages = adapt_messages_to_ollama(messages)

            assert adapted_messages == [
                {
                    'role': 'user',
                    'content': "What's in these images?",
                    'images': image_paths
                }
            ]

        def should_adapt_assistant_message(self):
            """
            Given an assistant message
            When adapting to Ollama format
            Then it should convert to the correct format
            """
            messages = [LLMMessage(role=MessageRole.Assistant, content="I am fine, thank you!")]

            adapted_messages = adapt_messages_to_ollama(messages)

            assert adapted_messages == [
                {
                    'role': 'assistant',
                    'content': 'I am fine, thank you!'
                }
            ]

    class DescribeToolMessages:
        """
        Specifications for adapting messages with tool calls and responses
        """

        def should_adapt_assistant_message_with_tool_call(self, tool_name, tool_arguments):
            """
            Given an assistant message with tool call
            When adapting to Ollama format
            Then it should convert the message and tool call to the correct format
            """
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

        def should_adapt_tool_response_message(self):
            """
            Given a tool response message
            When adapting to Ollama format
            Then it should convert to the correct format with string content
            """
            messages = [LLMMessage(role=MessageRole.Tool, content=json.dumps({"date": "Friday"}))]

            adapted_messages = adapt_messages_to_ollama(messages)

            assert adapted_messages == [
                {
                    'role': 'tool',
                    'content': '{"date": "Friday"}'  # must be a string
                }
            ]
