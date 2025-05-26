import logging
import threading
from time import sleep
from typing import Optional, Type
from uuid import uuid4

import structlog

from mojentic.event import TerminateEvent

logger = structlog.get_logger()


class Dispatcher:
    def __init__(self, router, shared_working_memory=None, batch_size=5, tracer=None):
        self.router = router
        self.batch_size = batch_size
        self.event_queue = []
        self._stop_event = threading.Event()
        self._thread = threading.Thread(target=self._dispatch_events)
        
        # Use null_tracer if no tracer is provided
        from mojentic.tracer import null_tracer
        self.tracer = tracer or null_tracer

        logger.debug("Starting event dispatch thread")
        self._thread.start()

    def stop(self):
        self._stop_event.set()
        self._thread.join()

    def dispatch(self, event):
        logger.log(logging.DEBUG, f"Dispatching event: {event}")
        if event.correlation_id is None:
            event.correlation_id = str(uuid4())
        self.event_queue.append(event)

    def _dispatch_events(self):
        while not self._stop_event.is_set():
            for _ in range(self.batch_size):
                logger.debug("Checking for events")
                if len(self.event_queue) > 0:
                    logger.debug(f"{len(self.event_queue)} events in queue")
                    event = self.event_queue.pop(0)
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
                        received_events = agent.receive_event(event)
                        logger.debug(f"Agent {agent} returned {len(events)} events")
                        events.extend(received_events)
                    for fe in events:
                        if type(fe) is TerminateEvent:
                            self._stop_event.set()
                        self.dispatch(fe)
            sleep(1)
