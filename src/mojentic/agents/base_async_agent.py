from typing import List

from mojentic.event import Event


class BaseAsyncAgent:
    """
    BaseAsyncAgent class is the base class for all asynchronous agents.
    It provides an async receive method for event processing.
    """

    async def receive_event_async(self, event: Event) -> List[Event]:
        """
        receive_event_async is the method that all async agents must implement. It takes an event as input and returns a list of
        events as output.

        In this way, you can perform work based on the event, and generate whatever subsequent events may need to be
        processed next.

        This keeps the agent decoupled from the specifics of the event routing and processing.

        Events are subclasses of the Event class.

        :param event: The event to process
        :return: A list of events to be processed next
        """
        return []
