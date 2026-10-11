from mojentic.agents.base_agent import BaseAgent
from mojentic.event import TerminateEvent


class OutputAgent(BaseAgent):
    def receive_event(self, event):
        print(event)
        return [TerminateEvent(source=type(self))]
