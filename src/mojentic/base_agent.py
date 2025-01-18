from typing import Annotated, List

from src.mojentic.event import Event
from src.mojentic.event_broker import EventBroker
from src.mojentic.tool import Tool


class BaseAgent:
    name: Annotated[str, "The name of the agent."]
    tools: Annotated[List[Tool], "The tools the agent has access to."]

    def __init__(self, event_broker: EventBroker):
        self.event_broker = event_broker

    def receive_event(self, event: Event):
        pass
