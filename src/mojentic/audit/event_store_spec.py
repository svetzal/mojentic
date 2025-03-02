from mojentic import Event
from mojentic.audit.event_store import EventStore


class DescribeEventStore:
    """
    The immutable event store is key to the auditability of agent interactions.
    """

    def should_store_an_event(self):
        """
        Given an event
        When asked to store the event
        Then the event should be stored
        """
        # Given
        event = Event(
            source=DescribeEventStore,
        )
        event_store = EventStore()

        # When
        event_store.store(event)

        # Then
        assert event in event_store.events