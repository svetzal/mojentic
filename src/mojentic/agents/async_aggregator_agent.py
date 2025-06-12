import asyncio
import structlog

from mojentic.agents.base_async_agent import BaseAsyncAgent
from mojentic.event import Event

logger = structlog.get_logger()


class AsyncAggregatorAgent(BaseAsyncAgent):
    """
    AsyncAggregatorAgent is an asynchronous version of the BaseAggregatingAgent.
    It aggregates events based on their correlation_id and processes them when all required events are available.
    """
    def __init__(self, event_types_needed=None):
        """
        Initialize the AsyncAggregatorAgent.

        Parameters
        ----------
        event_types_needed : list, optional
            List of event types that need to be captured before processing
        """
        super().__init__()
        self.results = {}
        self.event_types_needed = event_types_needed or []
        self.futures = {}  # Maps correlation_id to Future objects

    async def _get_and_reset_results(self, event):
        """
        Get and reset the results for a specific correlation_id.

        Parameters
        ----------
        event : Event
            The event to get results for

        Returns
        -------
        list
            The results for the event
        """
        results = self.results[event.correlation_id]
        self.results[event.correlation_id] = None
        return results

    async def _capture_results_if_needed(self, event):
        """
        Capture results for a specific correlation_id.

        Parameters
        ----------
        event : Event
            The event to capture results for
        """
        results = self.results.get(event.correlation_id, [])
        results.append(event)
        self.results[event.correlation_id] = results

        # Check if we have all needed events and set the future if we do
        event_types_captured = [type(e) for e in self.results.get(event.correlation_id, [])]
        finished = all([event_type in event_types_captured for event_type in self.event_types_needed])

        if finished and event.correlation_id in self.futures:
            future = self.futures[event.correlation_id]
            if not future.done():
                future.set_result(self.results[event.correlation_id])

    async def _has_all_needed(self, event):
        """
        Check if all needed event types have been captured for a specific correlation_id.

        Parameters
        ----------
        event : Event
            The event to check

        Returns
        -------
        bool
            True if all needed event types have been captured, False otherwise
        """
        event_types_captured = [type(e) for e in self.results.get(event.correlation_id, [])]
        finished = all([event_type in event_types_captured for event_type in self.event_types_needed])
        logger.debug(f"Captured: {event_types_captured}, Needed: {self.event_types_needed}, Finished: {finished}")
        return finished

    async def wait_for_events(self, correlation_id, timeout=None):
        """
        Wait for all needed events for a specific correlation_id.

        Parameters
        ----------
        correlation_id : str
            The correlation_id to wait for
        timeout : float, optional
            The timeout in seconds

        Returns
        -------
        list
            The events for the correlation_id
        """
        if correlation_id not in self.futures:
            self.futures[correlation_id] = asyncio.Future()

        # If we already have all needed events, return them
        if correlation_id in self.results:
            event_types_captured = [type(e) for e in self.results.get(correlation_id, [])]
            if all([event_type in event_types_captured for event_type in self.event_types_needed]):
                return self.results[correlation_id]

        # Otherwise, wait for the future to be set
        try:
            return await asyncio.wait_for(self.futures[correlation_id], timeout)
        except asyncio.TimeoutError:
            logger.warning(f"Timeout waiting for events for correlation_id {correlation_id}")
            return self.results.get(correlation_id, [])

    async def receive_event_async(self, event: Event) -> list:
        """
        Receive an event and process it if all needed events are available.

        Parameters
        ----------
        event : Event
            The event to process

        Returns
        -------
        list
            The events to be processed next
        """
        # First capture the event
        await self._capture_results_if_needed(event)

        # Then check if we have all needed events
        event_types_captured = [type(e) for e in self.results.get(event.correlation_id, [])]
        finished = all([event_type in event_types_captured for event_type in self.event_types_needed])

        # If we have all needed events, process them
        if finished:
            return await self.process_events(await self._get_and_reset_results(event))

        return []

    async def process_events(self, events):
        """
        Process a list of events.
        This method should be overridden by subclasses.

        Parameters
        ----------
        events : list
            The events to process

        Returns
        -------
        list
            The events to be processed next
        """
        return []
