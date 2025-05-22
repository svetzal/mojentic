"""
Example script demonstrating the usage of the audit system.

This script shows how to set up an audit system and use it to track LLM calls, tool usage,
and agent interactions in a simple conversation scenario.
"""
import time
from pydantic import Field
from datetime import datetime

from mojentic.agents import BaseAgent
from mojentic.agents.base_llm_agent import BaseLLMAgent
from mojentic.audit.audit_events import LLMCallAuditEvent, ToolCallAuditEvent
from mojentic.audit.audit_system import AuditSystem
from mojentic.dispatcher import Dispatcher
from mojentic.event import Event
from mojentic.llm.gateways.file_gateway import FileGateway
from mojentic.llm.llm_broker import LLMBroker
from mojentic.llm.tools.current_datetime import CurrentDatetimeTool
from mojentic.router import Router


# Define example events
class RequestEvent(Event):
    text: str = Field(..., description="The user's query")


class ResponseEvent(Event):
    text: str = Field(..., description="The response to the user's query")


# Define agents
class ChatAgent(BaseLLMAgent):
    def receive_event(self, event):
        response = self.generate_response(event.text)
        return [ResponseEvent(source=type(self), correlation_id=event.correlation_id, text=response)]


class OutputAgent(BaseAgent):
    def receive_event(self, event):
        if isinstance(event, ResponseEvent):
            print(f"Assistant: {event.text}")
        return []


def print_audit_events(audit_system, event_type=None):
    """Print audit events of a specific type."""
    events = audit_system.get_events(event_type=event_type) if event_type else audit_system.get_events()
    print(f"\n{'-'*80}")
    if event_type:
        print(f"Audit Events of type {event_type.__name__}:")
    else:
        print(f"All Audit Events:")
    print(f"{'-'*80}")
    
    for i, event in enumerate(events, 1):
        event_time = datetime.fromtimestamp(event.timestamp).strftime("%H:%M:%S.%f")[:-3]
        print(f"{i}. [{event_time}] {type(event).__name__}")
        
        # Print event-specific details
        if hasattr(event, 'model'):
            print(f"   Model: {event.model}")
        if hasattr(event, 'content') and event.content:
            content_preview = event.content[:100] + "..." if len(event.content) > 100 else event.content
            print(f"   Content: {content_preview}")
        if hasattr(event, 'tool_name'):
            print(f"   Tool: {event.tool_name}")
            print(f"   Arguments: {event.arguments}")
        if hasattr(event, 'from_agent'):
            print(f"   From: {event.from_agent} → To: {event.to_agent}")
            print(f"   Event Type: {event.event_type}")
        
        print()


def main():
    """Run the audit demo."""
    # Create audit system
    audit_system = AuditSystem()
    
    # Create LLM broker with audit system
    # Using file gateway to avoid actual LLM API calls for the example
    llm = LLMBroker(
        model="demo-model", 
        gateway=FileGateway(response="I'm a simulated LLM response for demonstration purposes."),
        audit_system=audit_system
    )
    
    # Create a tool with audit system
    date_tool = CurrentDatetimeTool()
    date_tool.set_audit_system(audit_system)
    
    # Create agents
    request_agent = ChatAgent(llm, tools=[date_tool])
    output_agent = OutputAgent()
    
    # Set up router and dispatcher with audit system
    router = Router({
        RequestEvent: [request_agent],
        ResponseEvent: [output_agent]
    })
    
    dispatcher = Dispatcher(router, audit_system=audit_system)
    
    # Process a user message
    print("User: What time is it?")
    dispatcher.dispatch(RequestEvent(source=str, text="What time is it now?"))
    
    # Wait for processing
    time.sleep(2)
    
    # Print audit events
    print_audit_events(audit_system)
    
    # Print specific audit event types
    print_audit_events(audit_system, LLMCallAuditEvent)
    print_audit_events(audit_system, ToolCallAuditEvent)
    
    # Stop the dispatcher
    dispatcher.stop()


if __name__ == "__main__":
    main()