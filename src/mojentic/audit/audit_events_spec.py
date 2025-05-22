import time
from typing import Dict, List

from mojentic.audit.audit_events import (
    AuditEvent,
    LLMCallAuditEvent,
    LLMResponseAuditEvent,
    ToolCallAuditEvent,
    AgentInteractionAuditEvent
)


class DescribeAuditEvents:
    """
    Test the audit event classes to ensure they can be instantiated and have the required properties.
    """

    def should_create_base_audit_event(self):
        """
        Test creating a base audit event.
        """
        # Given / When
        event = AuditEvent(
            source=DescribeAuditEvents,
            timestamp=time.time()
        )
        
        # Then
        assert isinstance(event, AuditEvent)
        assert isinstance(event.timestamp, float)
        assert event.source == DescribeAuditEvents

    def should_create_llm_call_audit_event(self):
        """
        Test creating an LLM call audit event.
        """
        # Given / When
        messages = [{"role": "system", "content": "You are a helpful assistant"}]
        event = LLMCallAuditEvent(
            source=DescribeAuditEvents,
            timestamp=time.time(),
            model="test-model",
            messages=messages,
            temperature=0.7,
            tools=None
        )
        
        # Then
        assert isinstance(event, LLMCallAuditEvent)
        assert event.model == "test-model"
        assert event.messages == messages
        assert event.temperature == 0.7
        assert event.tools is None

    def should_create_llm_response_audit_event(self):
        """
        Test creating an LLM response audit event.
        """
        # Given / When
        event = LLMResponseAuditEvent(
            source=DescribeAuditEvents,
            timestamp=time.time(),
            model="test-model",
            content="This is a test response",
            call_duration_ms=150.5
        )
        
        # Then
        assert isinstance(event, LLMResponseAuditEvent)
        assert event.model == "test-model"
        assert event.content == "This is a test response"
        assert event.call_duration_ms == 150.5
        assert event.tool_calls is None

    def should_create_tool_call_audit_event(self):
        """
        Test creating a tool call audit event.
        """
        # Given / When
        arguments = {"query": "test query"}
        event = ToolCallAuditEvent(
            source=DescribeAuditEvents,
            timestamp=time.time(),
            tool_name="test-tool",
            arguments=arguments,
            result="test result",
            caller="TestAgent"
        )
        
        # Then
        assert isinstance(event, ToolCallAuditEvent)
        assert event.tool_name == "test-tool"
        assert event.arguments == arguments
        assert event.result == "test result"
        assert event.caller == "TestAgent"

    def should_create_agent_interaction_audit_event(self):
        """
        Test creating an agent interaction audit event.
        """
        # Given / When
        event = AgentInteractionAuditEvent(
            source=DescribeAuditEvents,
            timestamp=time.time(),
            from_agent="AgentA",
            to_agent="AgentB",
            event_type="RequestEvent",
            event_id="12345"
        )
        
        # Then
        assert isinstance(event, AgentInteractionAuditEvent)
        assert event.from_agent == "AgentA"
        assert event.to_agent == "AgentB"
        assert event.event_type == "RequestEvent"
        assert event.event_id == "12345"