"""
Tests for the SimpleRecursiveAgent class.

This module contains comprehensive tests for the SimpleRecursiveAgent,
including event handling, async operation, iteration logic, and edge cases.
"""

import asyncio

import pytest

from mojentic.agents.simple_recursive_agent import (
    EventEmitter,
    GoalAchievedEvent,
    GoalFailedEvent,
    GoalState,
    GoalSubmittedEvent,
    IterationCompletedEvent,
    SimpleRecursiveAgent,
)
from mojentic.llm.chat_session import ChatSession
from mojentic.llm.gateways.llm_gateway import LLMGateway
from mojentic.llm.gateways.models import LLMGatewayResponse
from mojentic.llm.llm_broker import LLMBroker
from scripts.inprocess_http import InProcessTokenizer


class ScriptedGateway(LLMGateway):
    def __init__(self):
        self.responses = ["DONE"]
        self.requests = []

    def complete(self, model, messages, **kwargs):
        self.requests.append([message.model_copy(deep=True) for message in messages])
        response = (
            self.responses.pop(0) if len(self.responses) > 1 else self.responses[0]
        )
        return LLMGatewayResponse(content=response)


@pytest.fixture
def llm_broker():
    return LLMBroker(
        tokenizer=InProcessTokenizer(), model="test", gateway=ScriptedGateway()
    )


class DescribeEventEmitter:
    """Tests for the EventEmitter class."""

    def should_allow_subscribing_to_events(self):
        emitter = EventEmitter()
        received = []
        callback = received.append

        unsubscribe = emitter.subscribe(GoalSubmittedEvent, callback)

        assert callable(unsubscribe)
        assert GoalSubmittedEvent in emitter.subscribers
        assert callback in emitter.subscribers[GoalSubmittedEvent]

    def should_allow_unsubscribing_from_events(self):
        emitter = EventEmitter()
        received = []
        callback = received.append

        unsubscribe = emitter.subscribe(GoalSubmittedEvent, callback)
        unsubscribe()

        assert callback not in emitter.subscribers[GoalSubmittedEvent]

    def should_emit_events_to_subscribers(self):
        emitter = EventEmitter()
        first, second = [], []
        callback1 = first.append
        callback2 = second.append
        state = GoalState(goal="test")
        event = GoalSubmittedEvent(state=state)

        emitter.subscribe(GoalSubmittedEvent, callback1)
        emitter.subscribe(GoalSubmittedEvent, callback2)
        emitter.emit(event)

        assert first == [event]
        assert second == [event]

    @pytest.mark.asyncio
    async def should_handle_async_callbacks(self):
        emitter = EventEmitter()
        completed = asyncio.Event()
        received = []

        async def async_callback(event):
            received.append(event)
            completed.set()

        state = GoalState(goal="test")
        event = GoalSubmittedEvent(state=state)

        emitter.subscribe(GoalSubmittedEvent, async_callback)
        emitter.emit(event)

        # Give the event loop a chance to process the async callback
        await completed.wait()

        # The async callback should have been called
        assert received == [event]


class DescribeGoalState:
    """Tests for the GoalState class."""

    def should_initialize_with_defaults(self):
        state = GoalState(goal="test goal")

        assert state.goal == "test goal"
        assert state.iteration == 0
        assert state.max_iterations == 5
        assert state.solution is None
        assert state.is_complete is False

    def should_allow_custom_max_iterations(self):
        state = GoalState(goal="test", max_iterations=10)

        assert state.max_iterations == 10


class DescribeSimpleRecursiveAgent:
    """Tests for the SimpleRecursiveAgent class."""

    def should_initialize_with_required_parameters(self, llm_broker):
        agent = SimpleRecursiveAgent(llm=llm_broker)

        assert agent.llm == llm_broker
        assert agent.max_iterations == 5
        assert agent.available_tools == []
        assert isinstance(agent.emitter, EventEmitter)
        assert isinstance(agent.chat, ChatSession)

    def should_initialize_with_custom_parameters(self, llm_broker, mocker):
        from mojentic.llm.tools.llm_tool import LLMTool

        mock_tool = mocker.Mock(spec=LLMTool)
        agent = SimpleRecursiveAgent(
            llm=llm_broker,
            max_iterations=10,
            available_tools=[mock_tool],
            system_prompt="Custom prompt",
        )

        assert agent.max_iterations == 10
        assert len(agent.available_tools) == 1
        assert agent.available_tools[0] == mock_tool

    def should_have_event_handlers_registered(self, llm_broker):
        agent = SimpleRecursiveAgent(llm=llm_broker)

        assert GoalSubmittedEvent in agent.emitter.subscribers
        assert IterationCompletedEvent in agent.emitter.subscribers

    @pytest.mark.asyncio
    async def should_solve_problem_with_immediate_success(self, llm_broker, mocker):
        agent = SimpleRecursiveAgent(llm=llm_broker, max_iterations=3)

        llm_broker.adapter.responses = ["DONE"]

        result = await agent.solve("Test problem")

        assert result == "DONE"

    @pytest.mark.asyncio
    async def should_solve_problem_with_multiple_iterations(self, llm_broker, mocker):
        agent = SimpleRecursiveAgent(llm=llm_broker, max_iterations=3)

        responses = [
            "Working on it...",
            "Still working...",
            "DONE",
        ]
        llm_broker.adapter.responses = responses

        result = await agent.solve("Test problem")

        assert result == "DONE"

    @pytest.mark.asyncio
    async def should_handle_explicit_failure(self, llm_broker, mocker):
        agent = SimpleRecursiveAgent(llm=llm_broker, max_iterations=3)

        llm_broker.adapter.responses = ["FAIL"]

        result = await agent.solve("Impossible problem")

        assert "Failed to solve" in result
        assert "FAIL" in result

    @pytest.mark.asyncio
    async def should_handle_max_iterations_reached(self, llm_broker, mocker):
        agent = SimpleRecursiveAgent(llm=llm_broker, max_iterations=2)

        llm_broker.adapter.responses = ["Still working on it..."]

        result = await agent.solve("Complex problem")

        assert "Best solution after 2 iterations" in result

    @pytest.mark.asyncio
    async def should_emit_goal_submitted_event(self, llm_broker, mocker):
        agent = SimpleRecursiveAgent(llm=llm_broker)
        event_received = []

        def capture_event(event):
            event_received.append(event)

        agent.emitter.subscribe(GoalSubmittedEvent, capture_event)
        llm_broker.adapter.responses = ["DONE"]

        await agent.solve("Test problem")

        assert len(event_received) == 1
        assert isinstance(event_received[0], GoalSubmittedEvent)
        assert event_received[0].state.goal == "Test problem"

    @pytest.mark.asyncio
    async def should_emit_iteration_completed_events(self, llm_broker, mocker):
        agent = SimpleRecursiveAgent(llm=llm_broker, max_iterations=3)
        events_received = []

        def capture_event(event):
            events_received.append(event)

        agent.emitter.subscribe(IterationCompletedEvent, capture_event)
        responses = ["Working...", "Still working...", "DONE"]
        llm_broker.adapter.responses = responses

        await agent.solve("Test problem")

        assert len(events_received) == 3
        assert all(isinstance(e, IterationCompletedEvent) for e in events_received)

    @pytest.mark.asyncio
    async def should_emit_goal_achieved_event(self, llm_broker, mocker):
        agent = SimpleRecursiveAgent(llm=llm_broker)
        event_received = []

        def capture_event(event):
            event_received.append(event)

        agent.emitter.subscribe(GoalAchievedEvent, capture_event)
        llm_broker.adapter.responses = ["DONE"]

        await agent.solve("Test problem")

        assert len(event_received) == 1
        assert isinstance(event_received[0], GoalAchievedEvent)

    @pytest.mark.asyncio
    async def should_emit_goal_failed_event(self, llm_broker, mocker):
        agent = SimpleRecursiveAgent(llm=llm_broker)
        event_received = []

        def capture_event(event):
            event_received.append(event)

        agent.emitter.subscribe(GoalFailedEvent, capture_event)
        llm_broker.adapter.responses = ["FAIL"]

        await agent.solve("Impossible problem")

        assert len(event_received) == 1
        assert isinstance(event_received[0], GoalFailedEvent)

    @pytest.mark.asyncio
    async def should_allow_caller_timeout_through_public_solve(self, llm_broker):
        agent = SimpleRecursiveAgent(llm=llm_broker)
        completed = asyncio.Event()
        agent.emitter.subscribe(GoalAchievedEvent, lambda event: completed.set())

        with pytest.raises(TimeoutError):
            async with asyncio.timeout(0):
                await agent.solve("Test problem")

        await completed.wait()
        assert llm_broker.adapter.requests[-1][-1].content.endswith(
            'If you have the answer, say only "DONE".\n'
        )

    @pytest.mark.asyncio
    async def should_use_public_gateway_for_chat_send(self, llm_broker):
        agent = SimpleRecursiveAgent(llm=llm_broker)

        result = await agent.solve("Test prompt")

        assert result == "DONE"
        assert len(llm_broker.adapter.requests) == 1
        assert "Test prompt" in llm_broker.adapter.requests[0][-1].content

    @pytest.mark.asyncio
    async def should_handle_case_insensitive_done_keyword(self, llm_broker, mocker):
        agent = SimpleRecursiveAgent(llm=llm_broker)

        test_cases = ["done", "DoNe", "DONE", "  DONE  "]

        for response_text in test_cases:
            llm_broker.adapter.responses = [response_text]
            result = await agent.solve("Test problem")
            assert result == response_text

    @pytest.mark.asyncio
    async def should_handle_case_insensitive_fail_keyword(self, llm_broker, mocker):
        agent = SimpleRecursiveAgent(llm=llm_broker)

        test_cases = ["fail", "FaIl", "FAIL"]

        for response_text in test_cases:
            llm_broker.adapter.responses = [response_text]
            result = await agent.solve("Test problem")
            assert "Failed to solve" in result

    @pytest.mark.asyncio
    async def should_include_goal_in_prompt(self, llm_broker, mocker):
        agent = SimpleRecursiveAgent(llm=llm_broker)

        await agent.solve("Find the meaning of life")

        assert "Find the meaning of life" in llm_broker.adapter.requests[0][-1].content

    @pytest.mark.asyncio
    async def should_increment_iteration_count(self, llm_broker, mocker):
        agent = SimpleRecursiveAgent(llm=llm_broker, max_iterations=3)
        iterations_seen = []

        def track_iteration(event):
            iterations_seen.append(event.state.iteration)

        agent.emitter.subscribe(IterationCompletedEvent, track_iteration)

        responses = ["Working...", "Still working...", "DONE"]
        llm_broker.adapter.responses = responses

        await agent.solve("Test problem")

        assert iterations_seen == [1, 2, 3]

    @pytest.mark.asyncio
    async def should_not_false_positive_done_on_prose_with_done_substring(
        self, llm_broker, mocker
    ):
        agent = SimpleRecursiveAgent(llm=llm_broker, max_iterations=2)

        responses = [
            "I've undone the previous step and am working on the next one.",
            "DONE - Finished.",
        ]
        llm_broker.adapter.responses = responses

        result = await agent.solve("Test problem")

        assert "DONE" in result
        assert "Finished" in result

    @pytest.mark.asyncio
    async def should_not_false_positive_fail_on_prose_with_fail_substring(
        self, llm_broker, mocker
    ):
        agent = SimpleRecursiveAgent(llm=llm_broker, max_iterations=2)

        responses = [
            "The system is failsafe by design and will not encounter issues.",
            "DONE - Completed successfully.",
        ]
        llm_broker.adapter.responses = responses

        result = await agent.solve("Test problem")

        assert "DONE" in result
        assert "Completed successfully" in result

    @pytest.mark.asyncio
    async def should_propagate_handler_exceptions_to_solve_caller(
        self, llm_broker, mocker
    ):
        agent = SimpleRecursiveAgent(llm=llm_broker, max_iterations=3)

        boom = RuntimeError("Handler exploded")

        async def exploding_handler(event):
            raise boom

        agent.emitter.subscribe(IterationCompletedEvent, exploding_handler)

        llm_broker.adapter.responses = ["In progress..."]

        with pytest.raises(RuntimeError, match="Handler exploded"):
            await agent.solve("Test problem")
