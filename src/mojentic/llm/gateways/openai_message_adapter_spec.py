import json

import pytest

from mojentic.llm.gateways.models import LLMMessage, MessageRole, LLMToolCall
from mojentic.llm.gateways.openai_messages_adapter import adapt_messages_to_openai


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


class DescribeOpenAIMessagesAdapter:
    """
    Specification for the OpenAI messages adapter which handles conversion of messages to OpenAI format.
    """

    class DescribeSimpleMessages:
        """
        Specifications for adapting simple messages without tool calls
        """

        def should_adapt_system_message(self):
            """
            Given a system message
            When adapting to OpenAI format
            Then it should convert to the correct format
            """
            messages = [LLMMessage(role=MessageRole.System, content="This is a system message")]

            adapted_messages = adapt_messages_to_openai(messages)

            assert adapted_messages == [
                {
                    'role': 'system',
                    'content': 'This is a system message'
                }
            ]

        def should_adapt_user_message(self):
            """
            Given a user message
            When adapting to OpenAI format
            Then it should convert to the correct format
            """
            messages = [LLMMessage(role=MessageRole.User, content="Hello, how are you?")]

            adapted_messages = adapt_messages_to_openai(messages)

            assert adapted_messages == [
                {
                    'role': 'user',
                    'content': 'Hello, how are you?'
                }
            ]

        def should_adapt_assistant_message(self):
            """
            Given an assistant message
            When adapting to OpenAI format
            Then it should convert to the correct format
            """
            messages = [LLMMessage(role=MessageRole.Assistant, content="I am fine, thank you!")]

            adapted_messages = adapt_messages_to_openai(messages)

            assert adapted_messages == [
                {
                    'role': 'assistant',
                    'content': 'I am fine, thank you!'
                }
            ]

        def should_adapt_user_message_with_image_paths(self, mocker):
            """
            Given a user message with image paths
            When adapting to OpenAI format
            Then it should convert to the correct format with structured content array
            """
            # Mock the open function to avoid reading actual files
            mock_file = mocker.mock_open(read_data=b'fake_image_data')
            mocker.patch('builtins.open', mock_file)

            # Mock base64 encoding to return a predictable value
            mock_b64encode = mocker.patch('base64.b64encode')
            mock_b64encode.return_value = b'ZmFrZV9pbWFnZV9kYXRhX2VuY29kZWQ='  # 'fake_image_data_encoded' in base64

            image_paths = ["/path/to/image1.jpg", "/path/to/image2.png"]
            messages = [LLMMessage(role=MessageRole.User, content="What's in these images?", image_paths=image_paths)]

            adapted_messages = adapt_messages_to_openai(messages)

            # The content should be a structured array with text and images
            assert adapted_messages == [
                {
                    'role': 'user',
                    'content': [
                        {
                            'type': 'text',
                            'text': "What's in these images?"
                        },
                        {
                            'type': 'image_url',
                            'image_url': {
                                'url': 'data:image/jpg;base64,ZmFrZV9pbWFnZV9kYXRhX2VuY29kZWQ='
                            }
                        },
                        {
                            'type': 'image_url',
                            'image_url': {
                                'url': 'data:image/png;base64,ZmFrZV9pbWFnZV9kYXRhX2VuY29kZWQ='
                            }
                        }
                    ]
                }
            ]

    class DescribeToolMessages:
        """
        Specifications for adapting messages with tool calls and responses
        """

        def should_adapt_assistant_message_with_tool_call(self, tool_name, tool_arguments):
            """
            Given an assistant message with tool call
            When adapting to OpenAI format
            Then it should convert the message and tool call to the correct format
            """
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

        def should_adapt_tool_response_message(self, tool_call):
            """
            Given a tool response message
            When adapting to OpenAI format
            Then it should convert to the correct format with tool call ID
            """
            messages = [LLMMessage(role=MessageRole.Tool, content='{"date": "Friday"}', tool_calls=[tool_call])]

            adapted_messages = adapt_messages_to_openai(messages)

            assert adapted_messages == [
                {
                    'role': 'tool',
                    'content': '{"date": "Friday"}',
                    'tool_call_id': tool_call.id
                }
            ]
