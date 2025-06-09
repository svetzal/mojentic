import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock

from mojentic.agents.async_aggregator_agent import AsyncAggregatorAgent
from mojentic.event import Event


class TestEvent1(Event):
    """A test event type 1."""
    message: str


class TestEvent2(Event):
    """A test event type 2."""
    data: str


class TestEvent3(Event):
    """A test event type 3."""
    value: int


class TestResultEvent(Event):
    """A test result event."""
    result: str


class TestAsyncAggregator(AsyncAggregatorAgent):
    """A test implementation of AsyncAggregatorAgent."""
    
    async def process_events(self, events):
        """Process the events and return a result event."""
        # Extract events by type
        event1 = next((e for e in events if isinstance(e, TestEvent1)), None)
        event2 = next((e for e in events if isinstance(e, TestEvent2)), None)
        
        if event1 and event2:
            # Create a result combining the events
            return [TestResultEvent(
                source=type(self),
                correlation_id=event1.correlation_id,
                result=f"{event1.message} - {event2.data}"
            )]
        return []


@pytest.fixture
def async_aggregator():
    """Create an AsyncAggregatorAgent for testing."""
    return AsyncAggregatorAgent(event_types_needed=[TestEvent1, TestEvent2])


@pytest.fixture
def test_async_aggregator():
    """Create a TestAsyncAggregator for testing."""
    return TestAsyncAggregator(event_types_needed=[TestEvent1, TestEvent2])


@pytest.mark.asyncio
async def test_async_aggregator_init():
    """Test that the AsyncAggregatorAgent initializes correctly."""
    agent = AsyncAggregatorAgent(event_types_needed=[TestEvent1, TestEvent2])
    
    assert agent.event_types_needed == [TestEvent1, TestEvent2]
    assert agent.results == {}
    assert agent.futures == {}


@pytest.mark.asyncio
async def test_async_aggregator_capture_results(async_aggregator):
    """Test that the AsyncAggregatorAgent captures results correctly."""
    event = TestEvent1(source=str, correlation_id="test-id", message="Hello")
    
    await async_aggregator._capture_results_if_needed(event)
    
    assert "test-id" in async_aggregator.results
    assert len(async_aggregator.results["test-id"]) == 1
    assert async_aggregator.results["test-id"][0] == event


@pytest.mark.asyncio
async def test_async_aggregator_has_all_needed(async_aggregator):
    """Test that the AsyncAggregatorAgent checks if all needed events are captured."""
    event1 = TestEvent1(source=str, correlation_id="test-id", message="Hello")
    event2 = TestEvent2(source=str, correlation_id="test-id", data="World")
    
    # Initially, we don't have all needed events
    assert not await async_aggregator._has_all_needed(event1)
    
    # Capture the first event
    await async_aggregator._capture_results_if_needed(event1)
    assert not await async_aggregator._has_all_needed(event1)
    
    # Capture the second event
    await async_aggregator._capture_results_if_needed(event2)
    assert await async_aggregator._has_all_needed(event2)


@pytest.mark.asyncio
async def test_async_aggregator_get_and_reset_results(async_aggregator):
    """Test that the AsyncAggregatorAgent gets and resets results correctly."""
    event1 = TestEvent1(source=str, correlation_id="test-id", message="Hello")
    event2 = TestEvent2(source=str, correlation_id="test-id", data="World")
    
    # Capture the events
    await async_aggregator._capture_results_if_needed(event1)
    await async_aggregator._capture_results_if_needed(event2)
    
    # Get and reset the results
    results = await async_aggregator._get_and_reset_results(event1)
    
    assert len(results) == 2
    assert results[0] == event1
    assert results[1] == event2
    assert async_aggregator.results["test-id"] is None


@pytest.mark.asyncio
async def test_async_aggregator_wait_for_events(async_aggregator):
    """Test that the AsyncAggregatorAgent waits for events correctly."""
    event1 = TestEvent1(source=str, correlation_id="test-id", message="Hello")
    event2 = TestEvent2(source=str, correlation_id="test-id", data="World")
    
    # Start waiting for events in a separate task
    wait_task = asyncio.create_task(async_aggregator.wait_for_events("test-id", timeout=1))
    
    # Capture the events
    await async_aggregator._capture_results_if_needed(event1)
    await async_aggregator._capture_results_if_needed(event2)
    
    # Wait for the task to complete
    results = await wait_task
    
    assert len(results) == 2
    assert results[0] == event1
    assert results[1] == event2


@pytest.mark.asyncio
async def test_async_aggregator_wait_for_events_timeout(async_aggregator):
    """Test that the AsyncAggregatorAgent handles timeouts correctly."""
    event1 = TestEvent1(source=str, correlation_id="test-id", message="Hello")
    
    # Capture only one event
    await async_aggregator._capture_results_if_needed(event1)
    
    # Wait for events with a short timeout
    results = await async_aggregator.wait_for_events("test-id", timeout=0.1)
    
    # We should get the partial results
    assert len(results) == 1
    assert results[0] == event1


@pytest.mark.asyncio
async def test_async_aggregator_receive_event_async(test_async_aggregator):
    """Test that the AsyncAggregatorAgent processes events correctly."""
    event1 = TestEvent1(source=str, correlation_id="test-id", message="Hello")
    event2 = TestEvent2(source=str, correlation_id="test-id", data="World")
    
    # Receive the first event - should not process yet
    result1 = await test_async_aggregator.receive_event_async(event1)
    assert result1 == []
    
    # Receive the second event - should process both events
    result2 = await test_async_aggregator.receive_event_async(event2)
    
    assert len(result2) == 1
    assert isinstance(result2[0], TestResultEvent)
    assert result2[0].result == "Hello - World"


@pytest.mark.asyncio
async def test_async_aggregator_receive_event_async_wrong_order(test_async_aggregator):
    """Test that the AsyncAggregatorAgent processes events correctly regardless of order."""
    event1 = TestEvent1(source=str, correlation_id="test-id", message="Hello")
    event2 = TestEvent2(source=str, correlation_id="test-id", data="World")
    
    # Receive the second event first - should not process yet
    result1 = await test_async_aggregator.receive_event_async(event2)
    assert result1 == []
    
    # Receive the first event - should process both events
    result2 = await test_async_aggregator.receive_event_async(event1)
    
    assert len(result2) == 1
    assert isinstance(result2[0], TestResultEvent)
    assert result2[0].result == "Hello - World"


@pytest.mark.asyncio
async def test_async_aggregator_receive_event_async_different_correlation_ids(test_async_aggregator):
    """Test that the AsyncAggregatorAgent handles different correlation_ids correctly."""
    event1_id1 = TestEvent1(source=str, correlation_id="id1", message="Hello")
    event2_id1 = TestEvent2(source=str, correlation_id="id1", data="World")
    
    event1_id2 = TestEvent1(source=str, correlation_id="id2", message="Goodbye")
    event2_id2 = TestEvent2(source=str, correlation_id="id2", data="Universe")
    
    # Receive events for id1
    await test_async_aggregator.receive_event_async(event1_id1)
    result1 = await test_async_aggregator.receive_event_async(event2_id1)
    
    # Receive events for id2
    await test_async_aggregator.receive_event_async(event1_id2)
    result2 = await test_async_aggregator.receive_event_async(event2_id2)
    
    # Check results for id1
    assert len(result1) == 1
    assert result1[0].result == "Hello - World"
    
    # Check results for id2
    assert len(result2) == 1
    assert result2[0].result == "Goodbye - Universe"


@pytest.mark.asyncio
async def test_async_aggregator_process_events_base_implementation(async_aggregator):
    """Test that the base process_events implementation returns an empty list."""
    event1 = TestEvent1(source=str, correlation_id="test-id", message="Hello")
    event2 = TestEvent2(source=str, correlation_id="test-id", data="World")
    
    events = [event1, event2]
    result = await async_aggregator.process_events(events)
    
    assert result == []