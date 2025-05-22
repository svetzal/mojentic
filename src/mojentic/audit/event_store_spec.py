import time
from typing import List

from mojentic import Event
from mojentic.audit.audit_events import AuditEvent, LLMCallAuditEvent, AgentInteractionAuditEvent
from mojentic.audit.event_store import EventStore


class TestEvent(Event):
    """A simple event for testing."""
    value: int


class TestAuditEvent(AuditEvent):
    """A simple audit event for testing."""
    value: int


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
        
    def should_filter_events_by_type(self):
        """
        Given several events of different types
        When filtered by a specific type
        Then only events of that type should be returned
        """
        # Given
        event_store = EventStore()
        event1 = Event(source=DescribeEventStore)
        event2 = TestEvent(source=DescribeEventStore, value=42)
        event3 = TestEvent(source=DescribeEventStore, value=43)
        event_store.store(event1)
        event_store.store(event2)
        event_store.store(event3)
        
        # When
        result = event_store.get_events(event_type=TestEvent)
        
        # Then
        assert len(result) == 2
        assert event1 not in result
        assert event2 in result
        assert event3 in result
    
    def should_filter_audit_events_by_time_range(self):
        """
        Given several audit events with different timestamps
        When filtered by time range
        Then only events within that time range should be returned
        """
        # Given
        event_store = EventStore()
        now = time.time()
        event1 = TestAuditEvent(source=DescribeEventStore, timestamp=now - 100, value=1)
        event2 = TestAuditEvent(source=DescribeEventStore, timestamp=now - 50, value=2)
        event3 = TestAuditEvent(source=DescribeEventStore, timestamp=now, value=3)
        event_store.store(event1)
        event_store.store(event2)
        event_store.store(event3)
        
        # When
        result = event_store.get_events(start_time=now - 75, end_time=now - 25)
        
        # Then
        assert len(result) == 1
        assert event1 not in result
        assert event2 in result
        assert event3 not in result
    
    def should_apply_custom_filter_function(self):
        """
        Given several events
        When filtered with a custom filter function
        Then only events matching the filter should be returned
        """
        # Given
        event_store = EventStore()
        event1 = TestEvent(source=DescribeEventStore, value=10)
        event2 = TestEvent(source=DescribeEventStore, value=20)
        event3 = TestEvent(source=DescribeEventStore, value=30)
        event_store.store(event1)
        event_store.store(event2)
        event_store.store(event3)
        
        # When
        result = event_store.get_events(filter_func=lambda e: isinstance(e, TestEvent) and e.value > 15)
        
        # Then
        assert len(result) == 2
        assert event1 not in result
        assert event2 in result
        assert event3 in result
    
    def should_clear_events(self):
        """
        Given several stored events
        When the event store is cleared
        Then all events should be removed
        """
        # Given
        event_store = EventStore()
        event_store.store(Event(source=DescribeEventStore))
        event_store.store(Event(source=DescribeEventStore))
        assert len(event_store.events) == 2
        
        # When
        event_store.clear()
        
        # Then
        assert len(event_store.events) == 0
    
    def should_get_last_n_events(self):
        """
        Given several events
        When requesting the last N events
        Then only the most recent N events should be returned
        """
        # Given
        event_store = EventStore()
        event1 = TestEvent(source=DescribeEventStore, value=1)
        event2 = TestEvent(source=DescribeEventStore, value=2)
        event3 = TestEvent(source=DescribeEventStore, value=3)
        event4 = Event(source=DescribeEventStore)
        event_store.store(event1)
        event_store.store(event2)
        event_store.store(event3)
        event_store.store(event4)
        
        # When
        result = event_store.get_last_n_events(2)
        
        # Then
        assert len(result) == 2
        assert event1 not in result
        assert event2 not in result
        assert event3 in result
        assert event4 in result
    
    def should_get_last_n_events_by_type(self):
        """
        Given several events of different types
        When requesting the last N events of a specific type
        Then only the most recent N events of that type should be returned
        """
        # Given
        event_store = EventStore()
        event1 = TestEvent(source=DescribeEventStore, value=1)
        event2 = Event(source=DescribeEventStore)
        event3 = TestEvent(source=DescribeEventStore, value=2)
        event4 = TestEvent(source=DescribeEventStore, value=3)
        event_store.store(event1)
        event_store.store(event2)
        event_store.store(event3)
        event_store.store(event4)
        
        # When
        result = event_store.get_last_n_events(2, event_type=TestEvent)
        
        # Then
        assert len(result) == 2
        assert event1 not in result
        assert event2 not in result
        assert event3 in result
        assert event4 in result