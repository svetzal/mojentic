"""
TracerSystem module for coordinating tracer events.

This provides a central system for recording, filtering, and querying tracer events.
"""
import time
from typing import Any, Callable, Dict, List, Optional, Type, Union

import structlog

from mojentic.tracer.tracer_events import (
    TracerEvent, 
    LLMCallTracerEvent,
    LLMResponseTracerEvent,
    ToolCallTracerEvent,
    AgentInteractionTracerEvent
)
from mojentic.tracer.event_store import EventStore
from mojentic.event import Event

logger = structlog.get_logger()


class TracerSystem:
    """
    Central system for capturing and querying tracer events.

    The TracerSystem is responsible for recording events related to LLM calls,
    tool usage, and agent interactions, providing a way to trace through the
    major events of the system.
    """

    def __init__(self, event_store: Optional[EventStore] = None, enabled: bool = True):
        """
        Initialize the tracer system.

        Parameters
        ----------
        event_store : EventStore, optional
            The event store to use for storing events. If None, a new EventStore will be created.
        enabled : bool, default=True
            Whether the tracer system is enabled. If False, no events will be recorded.
        """
        self.event_store = event_store or EventStore()
        self.enabled = enabled

    def record_event(self, event: TracerEvent) -> None:
        """
        Record a tracer event in the event store.

        Parameters
        ----------
        event : TracerEvent
            The tracer event to record.
        """
        if not self.enabled:
            return

        self.event_store.store(event)

    def record_llm_call(self, 
                      model: str, 
                      messages: List[Dict], 
                      temperature: float = 1.0,
                      tools: Optional[List[Dict]] = None,
                      source: Any = None,
                      correlation_id: str = None) -> None:
        """
        Record an LLM call event.

        Parameters
        ----------
        model : str
            The name of the LLM model being called.
        messages : List[Dict]
            The messages sent to the LLM.
        temperature : float, default=1.0
            The temperature setting for the LLM call.
        tools : List[Dict], optional
            The tools available to the LLM, if any.
        source : Any, optional
            The source of the event. If None, the TracerSystem class will be used.
        correlation_id : str, required
            UUID string that is copied from cause-to-affect for tracing events.
        """
        if not self.enabled:
            return

        event = LLMCallTracerEvent(
            source=source or type(self),
            timestamp=time.time(),
            model=model,
            messages=messages,
            temperature=temperature,
            tools=tools,
            correlation_id=correlation_id
        )
        self.event_store.store(event)

    def record_llm_response(self, 
                         model: str,
                         content: str,
                         tool_calls: Optional[List[Dict]] = None,
                         call_duration_ms: Optional[float] = None,
                         source: Any = None,
                         correlation_id: str = None) -> None:
        """
        Record an LLM response event.

        Parameters
        ----------
        model : str
            The name of the LLM model that responded.
        content : str
            The content of the LLM response.
        tool_calls : List[Dict], optional
            Any tool calls made by the LLM in its response.
        call_duration_ms : float, optional
            The duration of the LLM call in milliseconds.
        source : Any, optional
            The source of the event. If None, the TracerSystem class will be used.
        correlation_id : str, required
            UUID string that is copied from cause-to-affect for tracing events.
        """
        if not self.enabled:
            return

        event = LLMResponseTracerEvent(
            source=source or type(self),
            timestamp=time.time(),
            model=model,
            content=content,
            tool_calls=tool_calls,
            call_duration_ms=call_duration_ms,
            correlation_id=correlation_id
        )
        self.event_store.store(event)

    def record_tool_call(self,
                       tool_name: str,
                       arguments: Dict[str, Any],
                       result: Any,
                       caller: Optional[str] = None,
                       source: Any = None,
                       correlation_id: str = None) -> None:
        """
        Record a tool call event.

        Parameters
        ----------
        tool_name : str
            The name of the tool being called.
        arguments : Dict[str, Any]
            The arguments provided to the tool.
        result : Any
            The result returned by the tool.
        caller : str, optional
            The name of the agent or component calling the tool.
        source : Any, optional
            The source of the event. If None, the TracerSystem class will be used.
        correlation_id : str, required
            UUID string that is copied from cause-to-affect for tracing events.
        """
        if not self.enabled:
            return

        event = ToolCallTracerEvent(
            source=source or type(self),
            timestamp=time.time(),
            tool_name=tool_name,
            arguments=arguments,
            result=result,
            caller=caller,
            correlation_id=correlation_id
        )
        self.event_store.store(event)

    def record_agent_interaction(self,
                               from_agent: str,
                               to_agent: str,
                               event_type: str,
                               event_id: Optional[str] = None,
                               source: Any = None,
                               correlation_id: str = None) -> None:
        """
        Record an agent interaction event.

        Parameters
        ----------
        from_agent : str
            The name of the agent sending the event.
        to_agent : str
            The name of the agent receiving the event.
        event_type : str
            The type of event being processed.
        event_id : str, optional
            A unique identifier for the event.
        source : Any, optional
            The source of the event. If None, the TracerSystem class will be used.
        correlation_id : str, required
            UUID string that is copied from cause-to-affect for tracing events.
        """
        if not self.enabled:
            return

        event = AgentInteractionTracerEvent(
            source=source or type(self),
            timestamp=time.time(),
            from_agent=from_agent,
            to_agent=to_agent,
            event_type=event_type,
            event_id=event_id,
            correlation_id=correlation_id
        )
        self.event_store.store(event)

    def get_events(self, 
                  event_type: Optional[Type[TracerEvent]] = None, 
                  start_time: Optional[float] = None,
                  end_time: Optional[float] = None,
                  filter_func: Optional[Callable[[TracerEvent], bool]] = None) -> List[TracerEvent]:
        """
        Get tracer events from the store, optionally filtered.

        This is a convenience wrapper around the EventStore's get_events method,
        specifically for tracer events.

        Parameters
        ----------
        event_type : Type[TracerEvent], optional
            Filter events by this specific tracer event type.
        start_time : float, optional
            Include events with timestamp >= start_time.
        end_time : float, optional
            Include events with timestamp <= end_time.
        filter_func : Callable[[TracerEvent], bool], optional
            Custom filter function to apply to events.

        Returns
        -------
        List[TracerEvent]
            Events that match the filter criteria.
        """
        # First filter to only TracerEvents
        events = self.event_store.get_events(event_type=TracerEvent)

        # Then apply additional filters
        if event_type is not None:
            events = [e for e in events if isinstance(e, event_type)]

        if start_time is not None:
            events = [e for e in events if e.timestamp >= start_time]

        if end_time is not None:
            events = [e for e in events if e.timestamp <= end_time]

        if filter_func is not None:
            events = [e for e in events if filter_func(e)]

        return events

    def get_last_n_tracer_events(self, n: int, event_type: Optional[Type[TracerEvent]] = None) -> List[TracerEvent]:
        """
        Get the last N tracer events, optionally filtered by type.

        Parameters
        ----------
        n : int
            Number of events to return.
        event_type : Type[TracerEvent], optional
            Filter events by this specific tracer event type.

        Returns
        -------
        List[TracerEvent]
            The last N tracer events that match the filter criteria.
        """
        base_type = event_type or TracerEvent
        return self.event_store.get_last_n_events(n, event_type=base_type)

    def clear(self) -> None:
        """
        Clear all events from the event store.
        """
        self.event_store.clear()

    def enable(self) -> None:
        """
        Enable the tracer system.
        """
        self.enabled = True

    def disable(self) -> None:
        """
        Disable the tracer system.
        """
        self.enabled = False


# Import and use the null tracer directly in client code via:
# from mojentic.tracer import null_tracer
