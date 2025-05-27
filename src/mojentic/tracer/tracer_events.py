"""
Defines tracer event types for tracking system interactions.
"""
from typing import Any, Dict, List, Optional, Type
from datetime import datetime
import uuid

from pydantic import Field

from mojentic.event import Event


class TracerEvent(Event):
    """
    Base class for all tracer-specific events.

    Tracer events are used to track system interactions for observability purposes.
    They are distinct from regular events which are used for agent communication.
    """
    timestamp: float = Field(..., description="Timestamp when the event occurred")
    correlation_id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="UUID string that is copied from cause-to-affect for tracing events")

    def printable_summary(self) -> str:
        """
        Return a formatted string summary of the event.

        Returns
        -------
        str
            A formatted string with the event information.
        """
        event_time = datetime.fromtimestamp(self.timestamp).strftime("%H:%M:%S.%f")[:-3]
        return f"[{event_time}] {type(self).__name__} (correlation_id: {self.correlation_id})"


class LLMCallTracerEvent(TracerEvent):
    """
    Records when an LLM is called with specific messages.
    """
    model: str = Field(..., description="The LLM model that was used")
    messages: List[dict] = Field(..., description="The messages sent to the LLM")
    temperature: float = Field(1.0, description="The temperature setting used for the call")
    tools: Optional[List[Dict]] = Field(None, description="The tools available to the LLM, if any")

    def printable_summary(self) -> str:
        """Return a formatted summary of the LLM call event."""
        base_summary = super().printable_summary()
        summary = f"{base_summary}\n   Model: {self.model}"

        if self.messages:
            msg_count = len(self.messages)
            summary += f"\n   Messages: {msg_count} message{'s' if msg_count != 1 else ''}"

        if self.temperature != 1.0:
            summary += f"\n   Temperature: {self.temperature}"

        if self.tools:
            tool_names = [tool.get('name', 'unknown') for tool in self.tools]
            summary += f"\n   Available Tools: {', '.join(tool_names)}"

        return summary


class LLMResponseTracerEvent(TracerEvent):
    """
    Records when an LLM responds to a call.
    """
    model: str = Field(..., description="The LLM model that was used")
    content: str = Field(..., description="The content of the LLM response")
    tool_calls: Optional[List[Dict]] = Field(None, description="Any tool calls made by the LLM")
    call_duration_ms: Optional[float] = Field(None, description="Duration of the LLM call in milliseconds")

    def printable_summary(self) -> str:
        """Return a formatted summary of the LLM response event."""
        base_summary = super().printable_summary()
        summary = f"{base_summary}\n   Model: {self.model}"

        if self.content:
            content_preview = self.content[:100] + "..." if len(self.content) > 100 else self.content
            summary += f"\n   Content: {content_preview}"

        if self.tool_calls:
            tool_count = len(self.tool_calls)
            summary += f"\n   Tool Calls: {tool_count} call{'s' if tool_count != 1 else ''}"

        if self.call_duration_ms is not None:
            summary += f"\n   Duration: {self.call_duration_ms:.2f}ms"

        return summary


class ToolCallTracerEvent(TracerEvent):
    """
    Records when a tool is called during agent execution.
    """
    tool_name: str = Field(..., description="Name of the tool that was called")
    arguments: Dict[str, Any] = Field(..., description="Arguments provided to the tool")
    result: Any = Field(..., description="Result returned by the tool")
    caller: Optional[str] = Field(None, description="Name of the agent or component that called the tool")

    def printable_summary(self) -> str:
        """Return a formatted summary of the tool call event."""
        base_summary = super().printable_summary()
        summary = f"{base_summary}\n   Tool: {self.tool_name}"

        if self.arguments:
            summary += f"\n   Arguments: {self.arguments}"

        if self.result is not None:
            result_str = str(self.result)
            result_preview = result_str[:100] + "..." if len(result_str) > 100 else result_str
            summary += f"\n   Result: {result_preview}"

        if self.caller:
            summary += f"\n   Caller: {self.caller}"

        return summary


class AgentInteractionTracerEvent(TracerEvent):
    """
    Records interactions between agents.
    """
    from_agent: str = Field(..., description="Name of the agent sending the event")
    to_agent: str = Field(..., description="Name of the agent receiving the event")
    event_type: str = Field(..., description="Type of event being processed")
    event_id: Optional[str] = Field(None, description="Unique identifier for the event")

    def printable_summary(self) -> str:
        """Return a formatted summary of the agent interaction event."""
        base_summary = super().printable_summary()
        summary = f"{base_summary}\n   From: {self.from_agent} → To: {self.to_agent}"
        summary += f"\n   Event Type: {self.event_type}"

        if self.event_id:
            summary += f"\n   Event ID: {self.event_id}"

        return summary
