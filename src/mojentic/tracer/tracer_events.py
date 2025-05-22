"""
Defines tracer event types for tracking system interactions.
"""
from typing import Any, Dict, List, Optional, Type

from pydantic import Field

from mojentic.event import Event


class TracerEvent(Event):
    """
    Base class for all tracer-specific events.
    
    Tracer events are used to track system interactions for observability purposes.
    They are distinct from regular events which are used for agent communication.
    """
    timestamp: float = Field(..., description="Timestamp when the event occurred")
    

class LLMCallTracerEvent(TracerEvent):
    """
    Records when an LLM is called with specific messages.
    """
    model: str = Field(..., description="The LLM model that was used")
    messages: List[dict] = Field(..., description="The messages sent to the LLM")
    temperature: float = Field(1.0, description="The temperature setting used for the call")
    tools: Optional[List[Dict]] = Field(None, description="The tools available to the LLM, if any")
    

class LLMResponseTracerEvent(TracerEvent):
    """
    Records when an LLM responds to a call.
    """
    model: str = Field(..., description="The LLM model that was used")
    content: str = Field(..., description="The content of the LLM response")
    tool_calls: Optional[List[Dict]] = Field(None, description="Any tool calls made by the LLM")
    call_duration_ms: Optional[float] = Field(None, description="Duration of the LLM call in milliseconds")


class ToolCallTracerEvent(TracerEvent):
    """
    Records when a tool is called during agent execution.
    """
    tool_name: str = Field(..., description="Name of the tool that was called")
    arguments: Dict[str, Any] = Field(..., description="Arguments provided to the tool")
    result: Any = Field(..., description="Result returned by the tool")
    caller: Optional[str] = Field(None, description="Name of the agent or component that called the tool")


class AgentInteractionTracerEvent(TracerEvent):
    """
    Records interactions between agents.
    """
    from_agent: str = Field(..., description="Name of the agent sending the event")
    to_agent: str = Field(..., description="Name of the agent receiving the event")
    event_type: str = Field(..., description="Type of event being processed")
    event_id: Optional[str] = Field(None, description="Unique identifier for the event")