from typing import Any, Callable, Dict, List, Optional, Type, Union
import time
from datetime import datetime

from mojentic.event import Event
from mojentic.tracer.tracer_events import TracerEvent


class EventStore:
    """
    Store for capturing and querying events, particularly useful for tracer events.
    """
    def __init__(self, on_store_callback: Optional[Callable[[Event], None]] = None):
        """
        Initialize an EventStore.

        Parameters
        ----------
        on_store_callback : Callable[[Event], None], optional
            A callback function that will be called whenever an event is stored.
            The callback receives the stored event as its argument.
        """
        self.events = []
        self.on_store_callback = on_store_callback

    def store(self, event: Event) -> None:
        """
        Store an event in the event store.

        Parameters
        ----------
        event : Event
            The event to store.
        """
        self.events.append(event)

        # Call the callback if it exists
        if self.on_store_callback is not None:
            self.on_store_callback(event)

    def get_events(self, 
                  event_type: Optional[Type[Event]] = None, 
                  start_time: Optional[float] = None,
                  end_time: Optional[float] = None,
                  filter_func: Optional[Callable[[Event], bool]] = None) -> List[Event]:
        """
        Get events from the store, optionally filtered by type, time range, and custom filter function.

        Parameters
        ----------
        event_type : Type[Event], optional
            Filter events by this specific event type.
        start_time : float, optional
            Include events with timestamp >= start_time (only applies to TracerEvent types).
        end_time : float, optional
            Include events with timestamp <= end_time (only applies to TracerEvent types).
        filter_func : Callable[[Event], bool], optional
            Custom filter function to apply to events.

        Returns
        -------
        List[Event]
            Events that match the filter criteria.
        """
        result = self.events

        # Filter by event type if specified
        if event_type is not None:
            result = [e for e in result if isinstance(e, event_type)]

        # Filter by time range if dealing with TracerEvents
        if start_time is not None:
            result = [e for e in result if isinstance(e, TracerEvent) and e.timestamp >= start_time]

        if end_time is not None:
            result = [e for e in result if isinstance(e, TracerEvent) and e.timestamp <= end_time]

        # Apply custom filter function if provided
        if filter_func is not None:
            result = [e for e in result if filter_func(e)]

        return result

    def clear(self) -> None:
        """
        Clear all events from the store.
        """
        self.events = []

    def get_last_n_events(self, n: int, event_type: Optional[Type[Event]] = None) -> List[Event]:
        """
        Get the last N events, optionally filtered by type.

        Parameters
        ----------
        n : int
            Number of events to return.
        event_type : Type[Event], optional
            Filter events by this specific event type.

        Returns
        -------
        List[Event]
            The last N events that match the filter criteria.
        """
        if event_type is not None:
            filtered = [e for e in self.events if isinstance(e, event_type)]
        else:
            filtered = self.events

        return filtered[-n:] if n < len(filtered) else filtered
