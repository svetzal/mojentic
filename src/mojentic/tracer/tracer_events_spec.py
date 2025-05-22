import time
from typing import Dict, List

from mojentic.tracer.tracer_events import (
    TracerEvent,
    LLMCallTracerEvent,
    LLMResponseTracerEvent,
    ToolCallTracerEvent,
    AgentInteractionTracerEvent
)


class DescribeTracerEvents:
    """
    Test the tracer event classes to ensure they can be instantiated and have the required properties.
    """

    def should_create_base_tracer_event(self):
        """
        Test creating a base tracer event.
        """
        # Given / When
        event = TracerEvent(
            source=DescribeTracerEvents,
            timestamp=time.time()
        )
        
        # Then
        assert isinstance(event, TracerEvent)
        assert isinstance(event.timestamp, float)
        assert event.source == DescribeTracerEvents

    def should_create_llm_call_tracer_event(self):
        """
        Test creating an LLM call tracer event.
        """
        # Given / When
        messages = [{"role": "system", "content": "You are a helpful assistant"}]
        event = LLMCallTracerEvent(
            source=DescribeTracerEvents,
            timestamp=time.time(),
            model="test-model",
            messages=messages,
            temperature=0.7,
            tools=None
        )
        
        # Then
        assert isinstance(event, LLMCallTracerEvent)
        assert event.model == "test-model"
        assert event.messages == messages
        assert event.temperature == 0.7
        assert event.tools is None

    def should_create_llm_response_tracer_event(self):
        """
        Test creating an LLM response tracer event.
        """
        # Given / When
        event = LLMResponseTracerEvent(
            source=DescribeTracerEvents,
            timestamp=time.time(),
            model="test-model",
            content="This is a test response",
            call_duration_ms=150.5
        )
        
        # Then
        assert isinstance(event, LLMResponseTracerEvent)
        assert event.model == "test-model"
        assert event.content == "This is a test response"
        assert event.call_duration_ms == 150.5
        assert event.tool_calls is None

    def should_create_tool_call_tracer_event(self):
        """
        Test creating a tool call tracer event.
        """
        # Given / When
        arguments = {"query": "test query"}
        event = ToolCallTracerEvent(
            source=DescribeTracerEvents,
            timestamp=time.time(),
            tool_name="test-tool",
            arguments=arguments,
            result="test result",
            caller="TestAgent"
        )
        
        # Then
        assert isinstance(event, ToolCallTracerEvent)
        assert event.tool_name == "test-tool"
        assert event.arguments == arguments
        assert event.result == "test result"
        assert event.caller == "TestAgent"

    def should_create_agent_interaction_tracer_event(self):
        """
        Test creating an agent interaction tracer event.
        """
        # Given / When
        event = AgentInteractionTracerEvent(
            source=DescribeTracerEvents,
            timestamp=time.time(),
            from_agent="AgentA",
            to_agent="AgentB",
            event_type="RequestEvent",
            event_id="12345"
        )
        
        # Then
        assert isinstance(event, AgentInteractionTracerEvent)
        assert event.from_agent == "AgentA"
        assert event.to_agent == "AgentB"
        assert event.event_type == "RequestEvent"
        assert event.event_id == "12345"