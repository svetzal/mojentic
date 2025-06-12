import asyncio
import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock

from mojentic.async_dispatcher import AsyncDispatcher
from mojentic.event import Event, TerminateEvent
from mojentic.agents.base_async_agent import BaseAsyncAgent
from mojentic.router import Router


class SampleEvent(Event):
    """A simple event for testing."""
    message: str


class SampleResponseEvent(Event):
    """A response event for testing."""
    response: str


class AsyncTestAgent(BaseAsyncAgent):
    """A test async agent that returns a SampleResponseEvent."""

    async def receive_event_async(self, event):
        if isinstance(event, SampleEvent):
            return [SampleResponseEvent(
                source=type(self),
                correlation_id=event.correlation_id,
                response=f"Processed: {event.message}"
            )]
        return []


class SyncTestAgent:
    """A test sync agent that returns a SampleResponseEvent."""

    def __init__(self):
        # Create a mock for tracking calls
        self._mock = MagicMock()

    def receive_event(self, event):
        # Track the call
        self._mock(event)

        if isinstance(event, SampleEvent):
            return [SampleResponseEvent(
                source=type(self),
                correlation_id=event.correlation_id,
                response=f"Processed sync: {event.message}"
            )]
        return []

    def assert_called_once(self):
        # Delegate to the mock
        self._mock.assert_called_once()


@pytest.fixture
def router():
    """Create a router for testing."""
    return Router()


@pytest.fixture
def async_agent():
    """Create an async agent for testing."""
    return AsyncTestAgent()


@pytest.fixture
def sync_agent():
    """Create a sync agent for testing."""
    return SyncTestAgent()


@pytest_asyncio.fixture
async def dispatcher(router):
    """Create and start an AsyncDispatcher for testing."""
    dispatcher = AsyncDispatcher(router)
    await dispatcher.start()
    yield dispatcher
    await dispatcher.stop()


@pytest.mark.asyncio
async def test_async_dispatcher_init(router):
    """Test that the AsyncDispatcher initializes correctly."""
    dispatcher = AsyncDispatcher(router)

    assert dispatcher.router == router
    assert dispatcher.batch_size == 5
    assert len(dispatcher.event_queue) == 0
    assert dispatcher._task is None


@pytest.mark.asyncio
async def test_async_dispatcher_start_stop(router):
    """Test that the AsyncDispatcher starts and stops correctly."""
    dispatcher = AsyncDispatcher(router)

    # Start the dispatcher
    await dispatcher.start()
    assert dispatcher._task is not None
    assert not dispatcher._stop_event.is_set()

    # Stop the dispatcher
    await dispatcher.stop()
    assert dispatcher._stop_event.is_set()


@pytest.mark.asyncio
async def test_async_dispatcher_dispatch(dispatcher, router, async_agent):
    """Test that the AsyncDispatcher dispatches events correctly."""
    # Register the agent
    router.add_route(SampleEvent, async_agent)

    # Create and dispatch an event
    event = SampleEvent(source=str, message="Hello")
    dispatcher.dispatch(event)

    # Wait for the event to be processed
    await dispatcher.wait_for_empty_queue(timeout=1)

    # The event should have been processed and removed from the queue
    assert len(dispatcher.event_queue) == 0


@pytest.mark.asyncio
async def test_async_dispatcher_with_async_agent(dispatcher, router, async_agent):
    """Test that the AsyncDispatcher works with async agents."""
    # Register the agent
    router.add_route(SampleEvent, async_agent)

    # Create and dispatch an event
    event = SampleEvent(source=str, message="Hello")
    dispatcher.dispatch(event)

    # Wait for the event to be processed
    await dispatcher.wait_for_empty_queue(timeout=1)

    # The event should have been processed and removed from the queue
    assert len(dispatcher.event_queue) == 0


@pytest.mark.asyncio
async def test_async_dispatcher_with_sync_agent(dispatcher, router, sync_agent):
    """Test that the AsyncDispatcher works with sync agents."""
    # Register the agent
    router.add_route(SampleEvent, sync_agent)

    # Create and dispatch an event
    event = SampleEvent(source=str, message="Hello")
    dispatcher.dispatch(event)

    # Wait for the event to be processed
    await dispatcher.wait_for_empty_queue(timeout=1)

    # The event should have been processed and removed from the queue
    assert len(dispatcher.event_queue) == 0

    # Verify that the sync agent's receive_event method was called
    sync_agent.assert_called_once()


@pytest.mark.asyncio
async def test_async_dispatcher_terminate_event(dispatcher, router):
    """Test that the AsyncDispatcher handles TerminateEvent correctly."""
    # Create a mock agent that returns a TerminateEvent
    class TerminateAgent(BaseAsyncAgent):
        async def receive_event_async(self, event):
            return [TerminateEvent(source=type(self))]

    terminate_agent = TerminateAgent()

    # Register the agent
    router.add_route(SampleEvent, terminate_agent)

    # Create and dispatch an event
    event = SampleEvent(source=str, message="Hello")
    dispatcher.dispatch(event)

    # Wait a moment for the event to be processed
    await asyncio.sleep(0.5)

    # The dispatcher should have stopped
    assert dispatcher._stop_event.is_set()


@pytest.mark.asyncio
async def test_async_dispatcher_wait_for_empty_queue(dispatcher):
    """Test that wait_for_empty_queue works correctly."""
    # Queue is initially empty
    assert await dispatcher.wait_for_empty_queue() is True

    # Add multiple events to the queue to test batch processing
    for i in range(10):
        event = SampleEvent(source=str, message=f"Event {i}")
        dispatcher.dispatch(event)

    # Queue is not empty
    assert len(dispatcher.event_queue) > 0

    # Wait for the queue to be empty with a sufficient timeout
    # The dispatcher should process all events
    assert await dispatcher.wait_for_empty_queue(timeout=1) is True

    # Verify the queue is empty
    assert len(dispatcher.event_queue) == 0


@pytest.mark.asyncio
async def test_async_dispatcher_batch_processing(dispatcher, router, async_agent):
    """Test that the AsyncDispatcher processes events in batches."""
    # Register the agent
    router.add_route(SampleEvent, async_agent)

    # Set a small batch size
    dispatcher.batch_size = 2

    # Create and dispatch multiple events
    for i in range(5):
        event = SampleEvent(source=str, message=f"Event {i}")
        dispatcher.dispatch(event)

    # Wait for all events to be processed
    await dispatcher.wait_for_empty_queue(timeout=2)

    # All events should have been processed
    assert len(dispatcher.event_queue) == 0


@pytest.mark.asyncio
async def test_async_dispatcher_correlation_id(dispatcher):
    """Test that the AsyncDispatcher assigns correlation_id if not provided."""
    # Create an event without a correlation_id
    event = SampleEvent(source=str, message="Hello")
    assert event.correlation_id is None

    # Dispatch the event
    dispatcher.dispatch(event)

    # The event should now have a correlation_id
    assert event.correlation_id is not None
