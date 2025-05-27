import time
from typing import Dict, List, Optional, Type, Union

import pytest

from mojentic.tracer.tracer_events import (
    TracerEvent,
    LLMCallTracerEvent,
    LLMResponseTracerEvent,
    ToolCallTracerEvent,
    AgentInteractionTracerEvent
)
from mojentic.tracer.tracer_system import TracerSystem
from mojentic.tracer.event_store import EventStore


class DescribeTracerSystem:
    """
    Tests for the TracerSystem class.
    """

    def should_initialize_with_default_event_store(self):
        """
        Given no event store
        When initializing a tracer system
        Then it should create a default event store
        """
        # Given / When
        tracer_system = TracerSystem()

        # Then
        assert tracer_system.event_store is not None
        assert isinstance(tracer_system.event_store, EventStore)
        assert tracer_system.enabled is True

    def should_initialize_with_provided_event_store(self):
        """
        Given an event store
        When initializing a tracer system with it
        Then it should use the provided event store
        """
        # Given
        event_store = EventStore()

        # When
        tracer_system = TracerSystem(event_store=event_store)

        # Then
        assert tracer_system.event_store is event_store

    def should_record_llm_call(self):
        """
        Given an enabled tracer system
        When recording an LLM call
        Then it should store an LLMCallTracerEvent
        """
        # Given
        tracer_system = TracerSystem()

        # When
        messages = [{"role": "system", "content": "You are a helpful assistant."}]
        correlation_id = "test-correlation-id"
        tracer_system.record_llm_call("test-model", messages, 0.7, correlation_id=correlation_id)

        # Then
        events = tracer_system.get_events(event_type=LLMCallTracerEvent)
        assert len(events) == 1
        event = events[0]
        assert event.model == "test-model"
        assert event.messages == messages
        assert event.temperature == 0.7

    def should_record_llm_response(self):
        """
        Given an enabled tracer system
        When recording an LLM response
        Then it should store an LLMResponseTracerEvent
        """
        # Given
        tracer_system = TracerSystem()

        # When
        correlation_id = "test-correlation-id"
        tracer_system.record_llm_response(
            "test-model",
            "This is a test response",
            call_duration_ms=150.5,
            correlation_id=correlation_id
        )

        # Then
        events = tracer_system.get_events(event_type=LLMResponseTracerEvent)
        assert len(events) == 1
        event = events[0]
        assert event.model == "test-model"
        assert event.content == "This is a test response"
        assert event.call_duration_ms == 150.5

    def should_record_tool_call(self):
        """
        Given an enabled tracer system
        When recording a tool call
        Then it should store a ToolCallTracerEvent
        """
        # Given
        tracer_system = TracerSystem()

        # When
        arguments = {"query": "test query"}
        correlation_id = "test-correlation-id"
        tracer_system.record_tool_call(
            "test-tool",
            arguments,
            "test result",
            "TestAgent",
            correlation_id=correlation_id
        )

        # Then
        events = tracer_system.get_events(event_type=ToolCallTracerEvent)
        assert len(events) == 1
        event = events[0]
        assert event.tool_name == "test-tool"
        assert event.arguments == arguments
        assert event.result == "test result"
        assert event.caller == "TestAgent"

    def should_record_agent_interaction(self):
        """
        Given an enabled tracer system
        When recording an agent interaction
        Then it should store an AgentInteractionTracerEvent
        """
        # Given
        tracer_system = TracerSystem()

        # When
        correlation_id = "test-correlation-id"
        tracer_system.record_agent_interaction(
            "AgentA",
            "AgentB",
            "RequestEvent",
            "12345",
            correlation_id=correlation_id
        )

        # Then
        events = tracer_system.get_events(event_type=AgentInteractionTracerEvent)
        assert len(events) == 1
        event = events[0]
        assert event.from_agent == "AgentA"
        assert event.to_agent == "AgentB"
        assert event.event_type == "RequestEvent"
        assert event.event_id == "12345"

    def should_not_record_when_disabled(self):
        """
        Given a disabled tracer system
        When recording events
        Then no events should be stored
        """
        # Given
        tracer_system = TracerSystem(enabled=False)

        # When
        correlation_id = "test-correlation-id"
        tracer_system.record_llm_call("test-model", [], correlation_id=correlation_id)
        tracer_system.record_llm_response("test-model", "response", correlation_id=correlation_id)
        tracer_system.record_tool_call("test-tool", {}, "result", correlation_id=correlation_id)
        tracer_system.record_agent_interaction("AgentA", "AgentB", "Event", correlation_id=correlation_id)

        # Then
        assert len(tracer_system.get_events()) == 0

    def should_filter_events_by_time_range(self):
        """
        Given several tracer events with different timestamps
        When filtered by time range
        Then only events within that time range should be returned
        """
        # Given
        tracer_system = TracerSystem()

        # Create events with specific timestamps
        now = time.time()
        correlation_id = "test-correlation-id"
        tracer_system.event_store.store(
            LLMCallTracerEvent(source=DescribeTracerSystem, timestamp=now - 100, model="model1", messages=[], correlation_id=correlation_id)
        )
        tracer_system.event_store.store(
            LLMCallTracerEvent(source=DescribeTracerSystem, timestamp=now - 50, model="model2", messages=[], correlation_id=correlation_id)
        )
        tracer_system.event_store.store(
            LLMCallTracerEvent(source=DescribeTracerSystem, timestamp=now, model="model3", messages=[], correlation_id=correlation_id)
        )

        # When
        result = tracer_system.get_events(start_time=now - 75, end_time=now - 25)

        # Then
        assert len(result) == 1
        assert result[0].model == "model2"

    def should_get_last_n_tracer_events(self):
        """
        Given several tracer events of different types
        When requesting the last N tracer events of a specific type
        Then only the most recent N events of that type should be returned
        """
        # Given
        tracer_system = TracerSystem()

        correlation_id = "test-correlation-id"
        tracer_system.record_llm_call("model1", [], correlation_id=correlation_id)
        tracer_system.record_tool_call("tool1", {}, "result1", correlation_id=correlation_id)
        tracer_system.record_llm_call("model2", [], correlation_id=correlation_id)
        tracer_system.record_llm_call("model3", [], correlation_id=correlation_id)

        # When
        result = tracer_system.get_last_n_tracer_events(2, event_type=LLMCallTracerEvent)

        # Then
        assert len(result) == 2
        assert result[0].model == "model2"
        assert result[1].model == "model3"

    def should_enable_and_disable(self):
        """
        Given a tracer system
        When enabling and disabling it
        Then its enabled state should change accordingly
        """
        # Given
        tracer_system = TracerSystem(enabled=False)
        assert not tracer_system.enabled

        # When
        tracer_system.enable()

        # Then
        assert tracer_system.enabled

        # When
        tracer_system.disable()

        # Then
        assert not tracer_system.enabled

    def should_clear_events(self):
        """
        Given a tracer system with events
        When clearing events
        Then all events should be removed
        """
        # Given
        tracer_system = TracerSystem()
        correlation_id = "test-correlation-id"
        tracer_system.record_llm_call("model1", [], correlation_id=correlation_id)
        tracer_system.record_tool_call("tool1", {}, "result1", correlation_id=correlation_id)
        assert len(tracer_system.get_events()) == 2

        # When
        tracer_system.clear()

        # Then
        assert len(tracer_system.get_events()) == 0
