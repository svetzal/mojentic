import time
from typing import Dict, List, Optional, Type, Union

import pytest

from mojentic.audit.audit_events import (
    AuditEvent,
    LLMCallAuditEvent,
    LLMResponseAuditEvent,
    ToolCallAuditEvent,
    AgentInteractionAuditEvent
)
from mojentic.audit.audit_system import AuditSystem
from mojentic.audit.event_store import EventStore


class DescribeAuditSystem:
    """
    Tests for the AuditSystem class.
    """
    
    def should_initialize_with_default_event_store(self):
        """
        Given no event store
        When initializing an audit system
        Then it should create a default event store
        """
        # Given / When
        audit_system = AuditSystem()
        
        # Then
        assert audit_system.event_store is not None
        assert isinstance(audit_system.event_store, EventStore)
        assert audit_system.enabled is True
    
    def should_initialize_with_provided_event_store(self):
        """
        Given an event store
        When initializing an audit system with it
        Then it should use the provided event store
        """
        # Given
        event_store = EventStore()
        
        # When
        audit_system = AuditSystem(event_store=event_store)
        
        # Then
        assert audit_system.event_store is event_store
    
    def should_record_llm_call(self):
        """
        Given an enabled audit system
        When recording an LLM call
        Then it should store an LLMCallAuditEvent
        """
        # Given
        audit_system = AuditSystem()
        
        # When
        messages = [{"role": "system", "content": "You are a helpful assistant."}]
        audit_system.record_llm_call("test-model", messages, 0.7)
        
        # Then
        events = audit_system.get_events(event_type=LLMCallAuditEvent)
        assert len(events) == 1
        event = events[0]
        assert event.model == "test-model"
        assert event.messages == messages
        assert event.temperature == 0.7
        
    def should_record_llm_response(self):
        """
        Given an enabled audit system
        When recording an LLM response
        Then it should store an LLMResponseAuditEvent
        """
        # Given
        audit_system = AuditSystem()
        
        # When
        audit_system.record_llm_response(
            "test-model",
            "This is a test response",
            call_duration_ms=150.5
        )
        
        # Then
        events = audit_system.get_events(event_type=LLMResponseAuditEvent)
        assert len(events) == 1
        event = events[0]
        assert event.model == "test-model"
        assert event.content == "This is a test response"
        assert event.call_duration_ms == 150.5
        
    def should_record_tool_call(self):
        """
        Given an enabled audit system
        When recording a tool call
        Then it should store a ToolCallAuditEvent
        """
        # Given
        audit_system = AuditSystem()
        
        # When
        arguments = {"query": "test query"}
        audit_system.record_tool_call(
            "test-tool",
            arguments,
            "test result",
            "TestAgent"
        )
        
        # Then
        events = audit_system.get_events(event_type=ToolCallAuditEvent)
        assert len(events) == 1
        event = events[0]
        assert event.tool_name == "test-tool"
        assert event.arguments == arguments
        assert event.result == "test result"
        assert event.caller == "TestAgent"
        
    def should_record_agent_interaction(self):
        """
        Given an enabled audit system
        When recording an agent interaction
        Then it should store an AgentInteractionAuditEvent
        """
        # Given
        audit_system = AuditSystem()
        
        # When
        audit_system.record_agent_interaction(
            "AgentA",
            "AgentB",
            "RequestEvent",
            "12345"
        )
        
        # Then
        events = audit_system.get_events(event_type=AgentInteractionAuditEvent)
        assert len(events) == 1
        event = events[0]
        assert event.from_agent == "AgentA"
        assert event.to_agent == "AgentB"
        assert event.event_type == "RequestEvent"
        assert event.event_id == "12345"
        
    def should_not_record_when_disabled(self):
        """
        Given a disabled audit system
        When recording events
        Then no events should be stored
        """
        # Given
        audit_system = AuditSystem(enabled=False)
        
        # When
        audit_system.record_llm_call("test-model", [])
        audit_system.record_llm_response("test-model", "response")
        audit_system.record_tool_call("test-tool", {}, "result")
        audit_system.record_agent_interaction("AgentA", "AgentB", "Event")
        
        # Then
        assert len(audit_system.get_events()) == 0
        
    def should_filter_events_by_time_range(self):
        """
        Given several audit events with different timestamps
        When filtered by time range
        Then only events within that time range should be returned
        """
        # Given
        audit_system = AuditSystem()
        
        # Create events with specific timestamps
        now = time.time()
        audit_system.event_store.store(
            LLMCallAuditEvent(source=DescribeAuditSystem, timestamp=now - 100, model="model1", messages=[])
        )
        audit_system.event_store.store(
            LLMCallAuditEvent(source=DescribeAuditSystem, timestamp=now - 50, model="model2", messages=[])
        )
        audit_system.event_store.store(
            LLMCallAuditEvent(source=DescribeAuditSystem, timestamp=now, model="model3", messages=[])
        )
        
        # When
        result = audit_system.get_events(start_time=now - 75, end_time=now - 25)
        
        # Then
        assert len(result) == 1
        assert result[0].model == "model2"
        
    def should_get_last_n_audit_events(self):
        """
        Given several audit events of different types
        When requesting the last N audit events of a specific type
        Then only the most recent N events of that type should be returned
        """
        # Given
        audit_system = AuditSystem()
        
        audit_system.record_llm_call("model1", [])
        audit_system.record_tool_call("tool1", {}, "result1")
        audit_system.record_llm_call("model2", [])
        audit_system.record_llm_call("model3", [])
        
        # When
        result = audit_system.get_last_n_audit_events(2, event_type=LLMCallAuditEvent)
        
        # Then
        assert len(result) == 2
        assert result[0].model == "model2"
        assert result[1].model == "model3"
        
    def should_enable_and_disable(self):
        """
        Given an audit system
        When enabling and disabling it
        Then its enabled state should change accordingly
        """
        # Given
        audit_system = AuditSystem(enabled=False)
        assert not audit_system.enabled
        
        # When
        audit_system.enable()
        
        # Then
        assert audit_system.enabled
        
        # When
        audit_system.disable()
        
        # Then
        assert not audit_system.enabled
        
    def should_clear_events(self):
        """
        Given an audit system with events
        When clearing events
        Then all events should be removed
        """
        # Given
        audit_system = AuditSystem()
        audit_system.record_llm_call("model1", [])
        audit_system.record_tool_call("tool1", {}, "result1")
        assert len(audit_system.get_events()) == 2
        
        # When
        audit_system.clear()
        
        # Then
        assert len(audit_system.get_events()) == 0