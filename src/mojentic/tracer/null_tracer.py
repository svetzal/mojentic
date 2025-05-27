"""
NullTracer implementation to eliminate conditional checks in the code.

This module provides a NullTracer that implements the same interface as TracerSystem
but performs no operations, following the Null Object Pattern.
"""
from typing import Any, Callable, Dict, List, Optional, Type

from mojentic.tracer.tracer_events import TracerEvent


class NullTracer:
    """
    A no-op implementation of TracerSystem that silently discards all tracing operations.

    This class follows the Null Object Pattern to eliminate conditional checks in client code.
    All record methods are overridden to do nothing, and all query methods return empty results.
    """

    def __init__(self):
        """Initialize the NullTracer with disabled state."""
        self.enabled = False
        self.event_store = None

    def record_event(self, event: TracerEvent) -> None:
        """
        Do nothing implementation of record_event.

        Parameters
        ----------
        event : TracerEvent
            The tracer event to record (will be ignored).
        """
        # Do nothing
        pass

    def record_llm_call(self, 
                      model: str, 
                      messages: List[Dict], 
                      temperature: float = 1.0,
                      tools: Optional[List[Dict]] = None,
                      source: Any = None,
                      correlation_id: str = None) -> None:
        """
        Do nothing implementation of record_llm_call.

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
            The source of the event.
        correlation_id : str, optional
            UUID string that is copied from cause-to-affect for tracing events.
        """
        # Do nothing
        pass

    def record_llm_response(self, 
                         model: str,
                         content: str,
                         tool_calls: Optional[List[Dict]] = None,
                         call_duration_ms: Optional[float] = None,
                         source: Any = None,
                         correlation_id: str = None) -> None:
        """
        Do nothing implementation of record_llm_response.

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
            The source of the event.
        correlation_id : str, optional
            UUID string that is copied from cause-to-affect for tracing events.
        """
        # Do nothing
        pass

    def record_tool_call(self,
                       tool_name: str,
                       arguments: Dict[str, Any],
                       result: Any,
                       caller: Optional[str] = None,
                       source: Any = None,
                       correlation_id: str = None) -> None:
        """
        Do nothing implementation of record_tool_call.

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
            The source of the event.
        correlation_id : str, optional
            UUID string that is copied from cause-to-affect for tracing events.
        """
        # Do nothing
        pass

    def record_agent_interaction(self,
                               from_agent: str,
                               to_agent: str,
                               event_type: str,
                               event_id: Optional[str] = None,
                               source: Any = None,
                               correlation_id: str = None) -> None:
        """
        Do nothing implementation of record_agent_interaction.

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
            The source of the event.
        correlation_id : str, optional
            UUID string that is copied from cause-to-affect for tracing events.
        """
        # Do nothing
        pass

    def get_events(self, 
                  event_type: Optional[Type[TracerEvent]] = None, 
                  start_time: Optional[float] = None,
                  end_time: Optional[float] = None,
                  filter_func: Optional[Callable[[TracerEvent], bool]] = None) -> List[TracerEvent]:
        """
        Return an empty list for any get_events request.

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
            An empty list.
        """
        return []

    def get_last_n_tracer_events(self, n: int, event_type: Optional[Type[TracerEvent]] = None) -> List[TracerEvent]:
        """
        Return an empty list for any get_last_n_tracer_events request.

        Parameters
        ----------
        n : int
            Number of events to return.
        event_type : Type[TracerEvent], optional
            Filter events by this specific tracer event type.

        Returns
        -------
        List[TracerEvent]
            An empty list.
        """
        return []

    def clear(self) -> None:
        """Do nothing implementation of clear method."""
        pass

    def enable(self) -> None:
        """No-op method for interface compatibility."""
        pass

    def disable(self) -> None:
        """No-op method for interface compatibility."""
        pass
