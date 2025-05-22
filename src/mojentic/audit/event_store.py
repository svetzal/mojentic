from typing import Any, Callable, Dict, List, Optional, Type, Union
import time
from datetime import datetime

from mojentic.event import Event
from mojentic.audit.audit_events import AuditEvent


class EventStore:
    """
    Store for capturing and querying events, particularly useful for audit events.
    """
    def __init__(self):
        self.events = []

    def store(self, event: Event) -> None:
        """
        Store an event in the event store.
        
        Parameters
        ----------
        event : Event
            The event to store.
        """
        self.events.append(event)
        
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
            Include events with timestamp >= start_time (only applies to AuditEvent types).
        end_time : float, optional
            Include events with timestamp <= end_time (only applies to AuditEvent types).
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
            
        # Filter by time range if dealing with AuditEvents
        if start_time is not None:
            result = [e for e in result if isinstance(e, AuditEvent) and e.timestamp >= start_time]
            
        if end_time is not None:
            result = [e for e in result if isinstance(e, AuditEvent) and e.timestamp <= end_time]
            
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
