"""
Example script demonstrating the tracer system with ChatSession and tools.

This example shows how to use the tracer system to monitor an interactive 
chat session with LLMBroker and tools. When the user exits the session, 
the script displays a summary of all traced events.

It also demonstrates how correlation_id is used to trace related events
across the system, allowing you to track the flow of a request from start to finish.
"""
import uuid
from datetime import datetime

from mojentic.tracer import TracerSystem
from mojentic.tracer.tracer_events import LLMCallTracerEvent, LLMResponseTracerEvent, ToolCallTracerEvent
from mojentic.llm import ChatSession, LLMBroker
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
    """Run a chat session with tracer system to monitor interactions."""
    # Create a tracer system to monitor all interactions
    tracer = TracerSystem()

    # Create an LLM broker with the tracer
    llm_broker = LLMBroker(model="llama3.3-70b-32k", tracer=tracer)

    # Create a date resolver tool that will also use the tracer
    date_tool = ResolveDateTool(llm_broker=llm_broker, tracer=tracer)

    # Create a chat session with the broker and tool
    chat_session = ChatSession(llm_broker, tools=[date_tool])

    # Dictionary to store correlation_ids for each conversation turn
    # This allows us to track related events across the system
    conversation_correlation_ids = {}

    print("Welcome to the chat session with tracer demonstration!")
    print("Ask questions about dates (e.g., 'What day is next Friday?') or anything else.")
    print("Behind the scenes, the tracer system is recording all interactions.")
    print("Each interaction is assigned a unique correlation_id to trace related events.")
    print("Press Enter with no input to exit and see the trace summary.")
    print("-" * 80)

    # Interactive chat session
    turn_counter = 0
    while True:
        query = input("You: ")
        if not query:
            print("Exiting chat session...")
            break
        else:
            # Generate a unique correlation_id for this conversation turn
            # In a real system, this would be passed from the initiating event
            # to all downstream events to maintain the causal chain
            correlation_id = str(uuid.uuid4())
            turn_counter += 1
            conversation_correlation_ids[turn_counter] = correlation_id

            print(f"[Turn {turn_counter}, correlation_id: {correlation_id[:8]}...]")
            print("Assistant: ", end="")

            # For demonstration purposes, we'll use the chat_session normally
            # In a production system, you would modify ChatSession to accept and use correlation_id
            response = chat_session.send(query)

            # Alternatively, you could use the LLMBroker directly with correlation_id:
            # messages = [LLMMessage(role=MessageRole.User, content=query)]
            # response = llm_broker.generate(messages, tools=[date_tool], correlation_id=correlation_id)

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

    # Demonstrate filtering events by correlation_id
    print("\nFiltering events by correlation_id:")
    print("This is a powerful feature that allows you to trace all events related to a specific request")

    # If we have any conversation turns, show events for the first turn
    if conversation_correlation_ids:
        # Get the correlation_id for the first turn
        first_turn_id = 1
        first_correlation_id = conversation_correlation_ids.get(first_turn_id)

        if first_correlation_id:
            print(f"\nEvents for conversation turn {first_turn_id} (correlation_id: {first_correlation_id[:8]}...):")

            # Define a filter function that checks the correlation_id
            def filter_by_correlation_id(event):
                return event.correlation_id == first_correlation_id

            # Get all events with this correlation_id
            related_events = tracer.get_events(filter_func=filter_by_correlation_id)

            if related_events:
                print(f"Found {len(related_events)} related events")
                print_tracer_events(related_events)

                # Show how this helps trace the flow of a request
                print("\nThe correlation_id allows you to trace the complete flow of a request:")
                print("1. From the initial LLM call")
                print("2. To the LLM response")
                print("3. To any tool calls triggered by the LLM")
                print("4. And any subsequent LLM calls with the tool results")
                print("\nThis creates a complete audit trail for debugging and observability.")
            else:
                print("No events found with this correlation_id. This is unexpected and may indicate an issue.")

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
