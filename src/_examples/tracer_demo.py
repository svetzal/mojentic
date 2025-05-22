"""
Example script demonstrating the tracer system with real LLMBroker usage.

This example shows how to use the tracer system to record and analyze
LLM interactions, tool calls, and other system events in a real scenario.
"""
import time
from datetime import datetime

from mojentic.tracer import TracerSystem
from mojentic.tracer.tracer_events import LLMCallTracerEvent, LLMResponseTracerEvent, ToolCallTracerEvent
from mojentic.llm.llm_broker import LLMBroker
from mojentic.llm.gateways.models import LLMMessage, MessageRole
from mojentic.llm.tools.date_resolver import ResolveDateTool


def print_tracer_events(events):
    """Print tracer events using their printable_summary method."""
    print(f"\n{'-'*80}")
    print("Tracer Events:")
    print(f"{'-'*80}")
    
    for i, event in enumerate(events, 1):
        print(f"{i}. {event.printable_summary()}")
        print()


def main():
    """Run the tracer demo with real LLM interaction."""
    # Create a tracer system for monitoring
    tracer = TracerSystem()
    
    # Create an LLM broker with the tracer
    # For a real example, you would use your preferred model and gateway
    llm = LLMBroker(model="gpt-3.5-turbo", tracer=tracer)
    
    # Create a date resolver tool that will also use the tracer
    date_tool = ResolveDateTool(llm_broker=llm, tracer=tracer)
    
    print("Demonstrating tracer system with LLM and tool interaction...")
    
    # Simulate a conversation with the LLM
    messages = [
        LLMMessage(role=MessageRole.System, content="You are a helpful assistant."),
        LLMMessage(role=MessageRole.User, content="What's the date next Friday?")
    ]
    
    try:
        # Generate a response
        # Note: In a real environment, this would call the actual LLM
        # For this demo, we'll simulate the response
        print("Simulating LLM call (would require actual API credentials)...")
        
        # Instead of making an actual LLM call which requires credentials,
        # we'll manually record the events that would be generated
        
        # Simulate response time
        time.sleep(1)
        
        # Manually record events for demonstration
        tracer.record_llm_call(
            model="gpt-3.5-turbo",
            messages=[m.dict() for m in messages],
            temperature=0.7,
            tools=[date_tool.descriptor],
            source=LLMBroker
        )
        
        # Simulate LLM wanting to call the date tool
        tracer.record_llm_response(
            model="gpt-3.5-turbo",
            content="I need to use a tool to answer that question.",
            tool_calls=[{
                "id": "call_123",
                "name": "resolve_date",
                "arguments": {"date_expression": "next Friday"}
            }],
            call_duration_ms=450.25,
            source=LLMBroker
        )
        
        # Simulate tool call
        tracer.record_tool_call(
            tool_name="resolve_date",
            arguments={"date_expression": "next Friday"},
            result="2023-05-26",
            caller="LLMBroker",
            source=ResolveDateTool
        )
        
        # Simulate final response
        tracer.record_llm_call(
            model="gpt-3.5-turbo",
            messages=[m.dict() for m in messages] + [
                {"role": "assistant", "content": None, "tool_calls": [{"id": "call_123", "name": "resolve_date", "arguments": {"date_expression": "next Friday"}}]},
                {"role": "tool", "content": "2023-05-26", "tool_call_id": "call_123"}
            ],
            temperature=0.7,
            source=LLMBroker
        )
        
        tracer.record_llm_response(
            model="gpt-3.5-turbo",
            content="The date next Friday is May 26, 2023.",
            call_duration_ms=125.75,
            source=LLMBroker
        )
        
    except Exception as e:
        print(f"Error: {e}")
        print("This is expected in the demo without actual LLM credentials.")
        print("We've recorded simulated events to demonstrate the tracer system.")
    
    # Now let's query and display the tracer events
    print("\nQuerying tracer events recorded during the interaction...")
    
    # Get all events
    all_events = tracer.get_events()
    print(f"Total events recorded: {len(all_events)}")
    print_tracer_events(all_events)
    
    # Filter events by type
    print("\nFiltering events by type:")
    llm_calls = tracer.get_events(event_type=LLMCallTracerEvent)
    print(f"\nLLM Call Events: {len(llm_calls)}")
    print_tracer_events(llm_calls)
    
    llm_responses = tracer.get_events(event_type=LLMResponseTracerEvent)
    print(f"\nLLM Response Events: {len(llm_responses)}")
    print_tracer_events(llm_responses)
    
    tool_calls = tracer.get_events(event_type=ToolCallTracerEvent)
    print(f"\nTool Call Events: {len(tool_calls)}")
    print_tracer_events(tool_calls)
    
    # Get the last 2 events regardless of type
    print("\nGetting the last 2 events:")
    last_events = tracer.get_last_n_tracer_events(2)
    print_tracer_events(last_events)
    
    # Time-based filtering example
    print("\nTime-based filtering would look like:")
    print("events = tracer.get_events(start_time=start_timestamp, end_time=end_timestamp)")


if __name__ == "__main__":
    main()