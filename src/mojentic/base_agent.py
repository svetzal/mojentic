from mojentic.event import Event
from mojentic.event_broker import EventBroker


class BaseAgent():
    def __init__(self, event_broker: EventBroker):
        self.event_broker = event_broker

    def receive_event(self, event: Event):
        pass
