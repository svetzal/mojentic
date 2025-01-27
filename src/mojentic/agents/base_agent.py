from typing import List

from mojentic.event import Event


class BaseAgent():
    """
    BaseAgent class is the base class for all agents.
    """

    def receive_event(self, event: Event) -> List[Event]:
        """
        receive_event is the method that all agents must implement. It takes an event as input and returns a list of
        events as output.

        In this way, you can perform work based on the event, and generate whatever subsequent events may need to be
        processed next.

        This keeps the agent decoupled from the specifics of the event routing and processing.

        Events are subclasses of the Event class.

        :param event:
        :return:
        """
        return []
