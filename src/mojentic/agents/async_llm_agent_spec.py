import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from pydantic import BaseModel, Field

from mojentic.agents.async_llm_agent import BaseAsyncLLMAgent
from mojentic.event import Event
from mojentic.llm.llm_broker import LLMBroker
from mojentic.llm.gateways.models import LLMMessage, MessageRole


class TestEvent(Event):
    """A simple event for testing."""
    message: str


class TestResponse(BaseModel):
    """A simple response model for testing."""
    answer: str = Field(..., description="The answer to the question")


@pytest.fixture
def mock_llm_broker():
    """Create a mock LLM broker for testing."""
    mock_broker = MagicMock(spec=LLMBroker)
    mock_broker.generate.return_value = "Test response"
    mock_broker.generate_object.return_value = TestResponse(answer="Test answer")
    return mock_broker


@pytest.fixture
def async_llm_agent(mock_llm_broker):
    """Create a BaseAsyncLLMAgent for testing."""
    return BaseAsyncLLMAgent(
        llm=mock_llm_broker,
        behaviour="You are a test assistant.",
        response_model=TestResponse
    )


@pytest.mark.asyncio
async def test_async_llm_agent_init(mock_llm_broker):
    """Test that the BaseAsyncLLMAgent initializes correctly."""
    agent = BaseAsyncLLMAgent(
        llm=mock_llm_broker,
        behaviour="You are a test assistant.",
        response_model=TestResponse
    )
    
    assert agent.llm == mock_llm_broker
    assert agent.behaviour == "You are a test assistant."
    assert agent.response_model == TestResponse
    assert agent.tools == []


@pytest.mark.asyncio
async def test_async_llm_agent_create_initial_messages(async_llm_agent):
    """Test that the BaseAsyncLLMAgent creates initial messages correctly."""
    messages = async_llm_agent._create_initial_messages()
    
    assert len(messages) == 1
    assert messages[0].role == MessageRole.System
    assert messages[0].content == "You are a test assistant."


@pytest.mark.asyncio
async def test_async_llm_agent_add_tool(async_llm_agent):
    """Test that the BaseAsyncLLMAgent can add tools."""
    mock_tool = MagicMock()
    async_llm_agent.add_tool(mock_tool)
    
    assert mock_tool in async_llm_agent.tools


@pytest.mark.asyncio
async def test_async_llm_agent_generate_response_with_model(async_llm_agent, mock_llm_broker):
    """Test that the BaseAsyncLLMAgent generates responses with a model."""
    response = await async_llm_agent.generate_response("Test question")
    
    # Verify that generate_object was called
    mock_llm_broker.generate_object.assert_called_once()
    
    # Verify the response
    assert isinstance(response, TestResponse)
    assert response.answer == "Test answer"


@pytest.mark.asyncio
async def test_async_llm_agent_generate_response_without_model(mock_llm_broker):
    """Test that the BaseAsyncLLMAgent generates responses without a model."""
    agent = BaseAsyncLLMAgent(
        llm=mock_llm_broker,
        behaviour="You are a test assistant."
    )
    
    response = await agent.generate_response("Test question")
    
    # Verify that generate was called
    mock_llm_broker.generate.assert_called_once()
    
    # Verify the response
    assert response == "Test response"


@pytest.mark.asyncio
async def test_async_llm_agent_generate_response_with_tools(mock_llm_broker):
    """Test that the BaseAsyncLLMAgent generates responses with tools."""
    mock_tool = MagicMock()
    
    agent = BaseAsyncLLMAgent(
        llm=mock_llm_broker,
        behaviour="You are a test assistant.",
        tools=[mock_tool]
    )
    
    response = await agent.generate_response("Test question")
    
    # Verify that generate was called with tools
    mock_llm_broker.generate.assert_called_once()
    args, kwargs = mock_llm_broker.generate.call_args
    assert kwargs.get('tools') == [mock_tool]


@pytest.mark.asyncio
async def test_async_llm_agent_receive_event_async(async_llm_agent):
    """Test that the BaseAsyncLLMAgent's receive_event_async method works."""
    event = TestEvent(source=str, message="Test message")
    
    # The base implementation should return an empty list
    result = await async_llm_agent.receive_event_async(event)
    
    assert result == []


# Create a subclass for testing the receive_event_async method
class TestAsyncLLMAgent(BaseAsyncLLMAgent):
    """A test async LLM agent that implements receive_event_async."""
    
    async def receive_event_async(self, event):
        if isinstance(event, TestEvent):
            response = await self.generate_response(event.message)
            return [TestEvent(
                source=type(self),
                correlation_id=event.correlation_id,
                message=f"Response: {response.answer}"
            )]
        return []


@pytest.mark.asyncio
async def test_subclass_async_llm_agent_receive_event_async(mock_llm_broker):
    """Test that a subclass of BaseAsyncLLMAgent can implement receive_event_async."""
    agent = TestAsyncLLMAgent(
        llm=mock_llm_broker,
        behaviour="You are a test assistant.",
        response_model=TestResponse
    )
    
    event = TestEvent(source=str, message="Test message")
    
    result = await agent.receive_event_async(event)
    
    assert len(result) == 1
    assert isinstance(result[0], TestEvent)
    assert result[0].message == "Response: Test answer"