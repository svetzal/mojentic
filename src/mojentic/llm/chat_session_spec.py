import pytest

from mojentic.llm.chat_session import ChatSession
from mojentic.llm.gateways.models import MessageRole

INTENDED_RESPONSE_MESSAGE = "Response message"


@pytest.fixture
def llm(mocker):
    llm = mocker.MagicMock()
    llm.generate.return_value = INTENDED_RESPONSE_MESSAGE
    return llm


@pytest.fixture
def tokenizer(mocker):
    tokenizer = mocker.MagicMock()
    tokenizer.encode.return_value = [1]  # Each message in the chat session will count as length 1
    return tokenizer


@pytest.fixture
def chat_session(llm, tokenizer):
    return ChatSession(llm=llm, system_prompt="You are a helpful assistant.", tokenizer_gateway=tokenizer,
                       max_context=3, temperature=1.0)


class DescribeChatSession:
    """
    Specification for the ChatSession class which handles chat-based interactions and chat history with LLMs.
    """

    class DescribeSessionInitialization:
        """
        Specifications for chat session initialization
        """

        def should_initialize_with_system_message_in_history(self, chat_session):
            """
            Given a new chat session
            When it is initialized
            Then it should contain only the system message
            """
            assert len(chat_session.messages) == 1
            assert chat_session.messages[0].role == MessageRole.System

    class DescribeMessageHandling:
        """
        Specifications for handling messages in the chat session
        """

        def should_respond_to_user_query_with_llm_response(self, chat_session):
            """
            Given a new chat session
            When sending a user query
            Then it should return the LLM's response
            """
            response = chat_session.send("Query message")
            assert response == INTENDED_RESPONSE_MESSAGE

    class DescribeSessionManagement:
        """
        Specifications for managing the chat session's message history
        """

        def should_grow_message_history_to_three_when_first_user_message_sent(self, chat_session):
            """
            Given a new chat session
            """
            _ = chat_session.send("Query message")
            assert len(chat_session.messages) == 3

        def should_respect_context_capacity(self, chat_session):
            """
            Given a chat session with limited context
            When sending multiple messages
            Then the message count should not exceed the capacity
            """
            _ = chat_session.send("Query message 1")
            _ = chat_session.send("Query message 2")
            assert len(chat_session.messages) == 3

        def should_maintain_newest_messages(self, chat_session):
            """
            Given a chat session at capacity of 3 tokens
            When sending new messages
            Then it should keep only the most recent message and response
            """
            _ = chat_session.send("Query message 1")
            _ = chat_session.send("Query message 2")

            assert chat_session.messages[0].role == MessageRole.System
            assert chat_session.messages[1].content == "Query message 2"
            assert chat_session.messages[2].content == INTENDED_RESPONSE_MESSAGE

    class DescribeMessageRoles:
        """
        Specifications for message role handling
        """

        def should_assign_correct_message_roles(self, chat_session):
            """
            Given a chat session with messages
            When examining message roles
            Then they should be correctly assigned
            """
            _ = chat_session.send("Query message")

            assert chat_session.messages[0].role == MessageRole.System
            assert chat_session.messages[1].role == MessageRole.User
            assert chat_session.messages[2].role == MessageRole.Assistant
