import asyncio
import logging
from collections import deque
from typing import Optional, Type
from uuid import uuid4

import structlog

from mojentic.event import TerminateEvent

logger = structlog.get_logger()


class AsyncDispatcher:
    """
    AsyncDispatcher class is an asynchronous version of the Dispatcher class.
    It uses asyncio and deque for event processing.
    """
    def __init__(self, router, shared_working_memory=None, batch_size=5, tracer=None):
        """
        Initialize the AsyncDispatcher.

        Parameters
        ----------
        router : Router
            The router to use for routing events to agents
        shared_working_memory : SharedWorkingMemory, optional
            The shared working memory to use
        batch_size : int, optional
            The number of events to process in each batch
        tracer : Tracer, optional
            The tracer to use for tracing events
        """
        self.router = router
        self.batch_size = batch_size
        self.event_queue = deque()
        self._stop_event = asyncio.Event()
        self._task = None

        # Use null_tracer if no tracer is provided
        from mojentic.tracer import null_tracer
        self.tracer = tracer or null_tracer

    async def start(self):
        """
        Start the event dispatch task.
        """
        logger.debug("Starting event dispatch task")
        self._task = asyncio.create_task(self._dispatch_events())
        return self

    async def stop(self):
        """
        Stop the event dispatch task.
        """
        self._stop_event.set()
        if self._task:
            await self._task

    async def wait_for_empty_queue(self, timeout=None):
        """
        Wait for the event queue to be empty.

        Parameters
        ----------
        timeout : float, optional
            The timeout in seconds

        Returns
        -------
        bool
            True if the queue is empty, False if the timeout was reached
        """
        start_time = asyncio.get_event_loop().time()
        while len(self.event_queue) > 0:
            if timeout is not None and asyncio.get_event_loop().time() - start_time > timeout:
                return False
            await asyncio.sleep(0.1)
        return True

    def dispatch(self, event):
        """
        Dispatch an event to the event queue.

        Parameters
        ----------
        event : Event
            The event to dispatch
        """
        logger.log(logging.DEBUG, f"Dispatching event: {event}")
        if event.correlation_id is None:
            event.correlation_id = str(uuid4())
        self.event_queue.append(event)

    async def _dispatch_events(self):
        """
        Dispatch events from the event queue to agents.
        """
        while not self._stop_event.is_set():
            for _ in range(self.batch_size):
                logger.debug("Checking for events")
                if len(self.event_queue) > 0:
                    logger.debug(f"{len(self.event_queue)} events in queue")
                    event = self.event_queue.popleft()
                    logger.debug(f"Processing event: {event}")
                    agents = self.router.get_agents(event)
                    logger.debug(f"Found {len(agents)} agents for event type {type(event)}")
                    events = []
                    for agent in agents:
                        logger.debug(f"Sending event to agent {agent}")

                        # Record agent interaction in tracer system
                        self.tracer.record_agent_interaction(
                            from_agent=str(event.source),
                            to_agent=str(type(agent)),
                            event_type=str(type(event).__name__),
                            event_id=event.correlation_id,
                            source=type(self)
                        )

                        # Process the event through the agent
                        # If the agent is an async agent, await its receive_event method
                        if hasattr(agent, 'receive_event_async'):
                            received_events = await agent.receive_event_async(event)
                        else:
                            received_events = agent.receive_event(event)

                        logger.debug(f"Agent {agent} returned {len(received_events)} events")
                        events.extend(received_events)
                    for fe in events:
                        if type(fe) is TerminateEvent:
                            self._stop_event.set()
                        self.dispatch(fe)
            await asyncio.sleep(0.1)  # Use asyncio.sleep instead of time.sleep
