import logging
import threading
from time import sleep
from uuid import uuid4

from mojentic.logger import logger


# This does a lot more than routing, perhaps splitting out a dispatcher or controller?
class Router:
    def __init__(self, routes=None, batch_size=5):
        if routes is None:
            routes = {}
        self.routes = routes
        self.batch_size = batch_size
        self.event_queue = []
        self._stop_event = threading.Event()
        self._thread = threading.Thread(target=self._dispatch_events)
        logger.debug("Starting event dispatch thread")
        self._thread.start()

    def stop(self):
        self._stop_event.set()
        self._thread.join()

    def add_route(self, event_type, agent):
        agents = self.routes.get(event_type, [])
        agents.append(agent)
        self.routes[event_type] = agents

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
                    agents = self.routes.get(type(event), [])
                    logger.debug(f"Found {len(agents)} agents for event type {type(event)}")
                    events = []
                    for agent in agents:
                        logger.debug(f"Sending event to agent {agent}")
                        received_events = agent.receive_event(event)
                        logger.debug(f"Agent {agent} returned {len(events)} events")
                        events.extend(received_events)
                    self.event_queue.extend(events)
            sleep(1)
