from typing import List

from mojentic import Event
from mojentic.agents import BaseLLMAgent


class AgentBroker:
    """
    Wraps an agent to allow participation in an asynchronous event-driven system.
    """

    def __init__(self, agent: BaseLLMAgent):
        self.agent = agent

    def receive_event(self, event: Event) -> List[Event]:
        """
        receive_event is called by the event broker when an event is to be received by an agent. The broker will return
        a list of events determined from the agent's output in response to the received event.

        In this way, you can perform work based on the event, and generate whatever subsequent events may need to be
        processed next.

        This keeps agents decoupled from the specifics of the event routing and processing.

        Events are subclasses of the Event class.

        :param event:
        :return:
        """
        return []
