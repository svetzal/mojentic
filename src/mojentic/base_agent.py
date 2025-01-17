from typing import Annotated, List

from event import Event
from tool import Tool


class BaseAgent:
    name: Annotated[str, "The name of the agent."]
    tools: Annotated[List[Tool], "The tools the agent has access to."]

    def __init__(self):
        pass

    def receive_event(self, event: Event):
        pass
