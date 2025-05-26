"""
Example script demonstrating the tracer system with ChatSession and tools.

This example shows how to use the tracer system to monitor an interactive 
chat session with LLMBroker and tools. When the user exits the session, 
the script displays a summary of all traced events.
"""
from datetime import datetime

from mojentic.tracer import TracerSystem
from mojentic.tracer.tracer_events import LLMCallTracerEvent, LLMResponseTracerEvent, ToolCallTracerEvent
from mojentic.llm import ChatSession, LLMBroker
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
    """Run a chat session with tracer system to monitor interactions."""
    # Create a tracer system to monitor all interactions
    tracer = TracerSystem()
    
    # Create an LLM broker with the tracer
    llm_broker = LLMBroker(model="llama3.3-70b-32k", tracer=tracer)
    
    # Create a date resolver tool that will also use the tracer
    date_tool = ResolveDateTool(llm_broker=llm_broker, tracer=tracer)
    
    # Create a chat session with the broker and tool
    chat_session = ChatSession(llm_broker, tools=[date_tool])
    
    print("Welcome to the chat session with tracer demonstration!")
    print("Ask questions about dates (e.g., 'What day is next Friday?') or anything else.")
    print("Behind the scenes, the tracer system is recording all interactions.")
    print("Press Enter with no input to exit and see the trace summary.")
    print("-" * 80)
    
    # Interactive chat session
    while True:
        query = input("You: ")
        if not query:
            print("Exiting chat session...")
            break
        else:
            print("Assistant: ", end="")
            response = chat_session.send(query)
            print(response)
    
    # After the user exits, display tracer event summary
    print("\nTracer System Summary")
    print("=" * 80)
    print(f"You just had a conversation with an LLM, and the tracer recorded everything!")
    
    # Get all events
    all_events = tracer.get_events()
    print(f"Total events recorded: {len(all_events)}")
    print_tracer_events(all_events)
    
    # Show how to filter events by type
    print("\nYou can filter events by type:")
    
    llm_calls = tracer.get_events(event_type=LLMCallTracerEvent)
    print(f"LLM Call Events: {len(llm_calls)}")
    if llm_calls:
        print(f"Example: {llm_calls[0].printable_summary()}")
    
    llm_responses = tracer.get_events(event_type=LLMResponseTracerEvent)
    print(f"LLM Response Events: {len(llm_responses)}")
    if llm_responses:
        print(f"Example: {llm_responses[0].printable_summary()}")
    
    tool_calls = tracer.get_events(event_type=ToolCallTracerEvent)
    print(f"Tool Call Events: {len(tool_calls)}")
    if tool_calls:
        print(f"Example: {tool_calls[0].printable_summary()}")
    
    # Show the last few events
    print("\nThe last few events:")
    last_events = tracer.get_last_n_tracer_events(3)
    print_tracer_events(last_events)
    
    # Show how to use time-based filtering
    print("\nYou can also filter events by time range:")
    print("Example: tracer.get_events(start_time=start_timestamp, end_time=end_timestamp)")
    
    # Show how to extract specific information from events
    if tool_calls:
        print("\nDetailed analysis example - Tool usage stats:")
        tool_names = {}
        for event in tool_calls:
            tool_name = event.tool_name
            tool_names[tool_name] = tool_names.get(tool_name, 0) + 1
        
        print("Tool usage frequency:")
        for tool_name, count in tool_names.items():
            print(f"  - {tool_name}: {count} calls")


if __name__ == "__main__":
    main()