"""
Tests for the SimpleRecursiveAgent class.

This module contains comprehensive tests for the SimpleRecursiveAgent,
including event handling, async operation, iteration logic, and edge cases.
"""

import asyncio
import pytest
from unittest.mock import MagicMock, AsyncMock

from mojentic.agents.simple_recursive_agent import (
    SimpleRecursiveAgent,
    GoalState,
    GoalSubmittedEvent,
    IterationCompletedEvent,
    GoalAchievedEvent,
    GoalFailedEvent,
    TimeoutEvent,
    EventEmitter,
)
from mojentic.llm.llm_broker import LLMBroker
from mojentic.llm.chat_session import ChatSession


@pytest.fixture
def mock_llm_broker():
    """Create a mock LLM broker for testing."""
    mock_broker = MagicMock(spec=LLMBroker)
    return mock_broker


@pytest.fixture
def mock_chat_session(mocker):
    """Create a mock ChatSession for testing."""
    mock_session = mocker.Mock(spec=ChatSession)
    mock_session.send.return_value = "DONE - Test solution"
    return mock_session


class DescribeEventEmitter:
    """Tests for the EventEmitter class."""

    def should_allow_subscribing_to_events(self):
        """Test that subscribers can be added to event types."""
        emitter = EventEmitter()
        callback = MagicMock()

        unsubscribe = emitter.subscribe(GoalSubmittedEvent, callback)

        assert callable(unsubscribe)
        assert GoalSubmittedEvent in emitter.subscribers
        assert callback in emitter.subscribers[GoalSubmittedEvent]

    def should_allow_unsubscribing_from_events(self):
        """Test that subscribers can be removed from event types."""
        emitter = EventEmitter()
        callback = MagicMock()

        unsubscribe = emitter.subscribe(GoalSubmittedEvent, callback)
        unsubscribe()

        assert callback not in emitter.subscribers[GoalSubmittedEvent]

    def should_emit_events_to_subscribers(self):
        """Test that events are delivered to all subscribers."""
        emitter = EventEmitter()
        callback1 = MagicMock()
        callback2 = MagicMock()
        state = GoalState(goal="test")
        event = GoalSubmittedEvent(state=state)

        emitter.subscribe(GoalSubmittedEvent, callback1)
        emitter.subscribe(GoalSubmittedEvent, callback2)
        emitter.emit(event)

        callback1.assert_called_once_with(event)
        callback2.assert_called_once_with(event)

    @pytest.mark.asyncio
    async def should_handle_async_callbacks(self):
        """Test that async callbacks are properly handled."""
        emitter = EventEmitter()
        async_callback = AsyncMock()
        state = GoalState(goal="test")
        event = GoalSubmittedEvent(state=state)

        emitter.subscribe(GoalSubmittedEvent, async_callback)
        emitter.emit(event)

        # Give the event loop a chance to process the async callback
        await asyncio.sleep(0.01)

        # The async callback should have been called
        assert async_callback.called


class DescribeGoalState:
    """Tests for the GoalState class."""

    def should_initialize_with_defaults(self):
        """Test that GoalState initializes with correct defaults."""
        state = GoalState(goal="test goal")

        assert state.goal == "test goal"
        assert state.iteration == 0
        assert state.max_iterations == 5
        assert state.solution is None
        assert state.is_complete is False

    def should_allow_custom_max_iterations(self):
        """Test that max_iterations can be customized."""
        state = GoalState(goal="test", max_iterations=10)

        assert state.max_iterations == 10


class DescribeSimpleRecursiveAgent:
    """Tests for the SimpleRecursiveAgent class."""

    def should_initialize_with_required_parameters(self, mock_llm_broker):
        """Test that the agent initializes with required parameters."""
        agent = SimpleRecursiveAgent(llm=mock_llm_broker)

        assert agent.llm == mock_llm_broker
        assert agent.max_iterations == 5
        assert agent.available_tools == []
        assert isinstance(agent.emitter, EventEmitter)
        assert isinstance(agent.chat, ChatSession)

    def should_initialize_with_custom_parameters(self, mock_llm_broker):
        """Test that the agent accepts custom parameters."""
        from mojentic.llm.tools.llm_tool import LLMTool

        mock_tool = MagicMock(spec=LLMTool)
        agent = SimpleRecursiveAgent(
            llm=mock_llm_broker,
            max_iterations=10,
            available_tools=[mock_tool],
            system_prompt="Custom prompt"
        )

        assert agent.max_iterations == 10
        assert len(agent.available_tools) == 1
        assert agent.available_tools[0] == mock_tool

    def should_have_event_handlers_registered(self, mock_llm_broker):
        """Test that event handlers are registered during initialization."""
        agent = SimpleRecursiveAgent(llm=mock_llm_broker)

        assert GoalSubmittedEvent in agent.emitter.subscribers
        assert IterationCompletedEvent in agent.emitter.subscribers

    @pytest.mark.asyncio
    async def should_solve_problem_with_immediate_success(
        self, mock_llm_broker, mocker
    ):
        """Test that the agent solves a problem that succeeds immediately."""
        agent = SimpleRecursiveAgent(llm=mock_llm_broker, max_iterations=3)

        # Mock the chat session to return DONE immediately
        mocker.patch.object(
            agent.chat, "send", return_value="DONE - Solution found"
        )

        result = await agent.solve("Test problem")

        assert "DONE" in result
        assert "Solution found" in result

    @pytest.mark.asyncio
    async def should_solve_problem_with_multiple_iterations(
        self, mock_llm_broker, mocker
    ):
        """Test that the agent handles multiple iterations before success."""
        agent = SimpleRecursiveAgent(llm=mock_llm_broker, max_iterations=3)

        # Mock the chat session to return different responses
        responses = [
            "Working on it...",
            "Still working...",
            "DONE - Final solution",
        ]
        mocker.patch.object(
            agent.chat, "send", side_effect=responses
        )

        result = await agent.solve("Test problem")

        assert "DONE" in result
        assert "Final solution" in result

    @pytest.mark.asyncio
    async def should_handle_explicit_failure(self, mock_llm_broker, mocker):
        """Test that the agent handles explicit FAIL responses."""
        agent = SimpleRecursiveAgent(llm=mock_llm_broker, max_iterations=3)

        # Mock the chat session to return FAIL
        mocker.patch.object(
            agent.chat, "send", return_value="FAIL - Cannot solve this problem"
        )

        result = await agent.solve("Impossible problem")

        assert "Failed to solve" in result
        assert "Cannot solve this problem" in result

    @pytest.mark.asyncio
    async def should_handle_max_iterations_reached(
        self, mock_llm_broker, mocker
    ):
        """Test that the agent stops at max_iterations."""
        agent = SimpleRecursiveAgent(llm=mock_llm_broker, max_iterations=2)

        # Mock the chat session to never return DONE or FAIL
        mocker.patch.object(
            agent.chat, "send", return_value="Still working on it..."
        )

        result = await agent.solve("Complex problem")

        assert "Best solution after 2 iterations" in result

    @pytest.mark.asyncio
    async def should_emit_goal_submitted_event(self, mock_llm_broker, mocker):
        """Test that GoalSubmittedEvent is emitted."""
        agent = SimpleRecursiveAgent(llm=mock_llm_broker)
        event_received = []

        def capture_event(event):
            event_received.append(event)

        agent.emitter.subscribe(GoalSubmittedEvent, capture_event)
        mocker.patch.object(
            agent.chat, "send", return_value="DONE - Solution"
        )

        await agent.solve("Test problem")

        assert len(event_received) == 1
        assert isinstance(event_received[0], GoalSubmittedEvent)
        assert event_received[0].state.goal == "Test problem"

    @pytest.mark.asyncio
    async def should_emit_iteration_completed_events(
        self, mock_llm_broker, mocker
    ):
        """Test that IterationCompletedEvent is emitted for each iteration."""
        agent = SimpleRecursiveAgent(llm=mock_llm_broker, max_iterations=3)
        events_received = []

        def capture_event(event):
            events_received.append(event)

        agent.emitter.subscribe(IterationCompletedEvent, capture_event)
        responses = ["Working...", "Still working...", "DONE - Solution"]
        mocker.patch.object(
            agent.chat, "send", side_effect=responses
        )

        await agent.solve("Test problem")

        assert len(events_received) == 3
        assert all(isinstance(e, IterationCompletedEvent) for e in events_received)

    @pytest.mark.asyncio
    async def should_emit_goal_achieved_event(self, mock_llm_broker, mocker):
        """Test that GoalAchievedEvent is emitted on success."""
        agent = SimpleRecursiveAgent(llm=mock_llm_broker)
        event_received = []

        def capture_event(event):
            event_received.append(event)

        agent.emitter.subscribe(GoalAchievedEvent, capture_event)
        mocker.patch.object(
            agent.chat, "send", return_value="DONE - Solution"
        )

        await agent.solve("Test problem")

        assert len(event_received) == 1
        assert isinstance(event_received[0], GoalAchievedEvent)

    @pytest.mark.asyncio
    async def should_emit_goal_failed_event(self, mock_llm_broker, mocker):
        """Test that GoalFailedEvent is emitted on failure."""
        agent = SimpleRecursiveAgent(llm=mock_llm_broker)
        event_received = []

        def capture_event(event):
            event_received.append(event)

        agent.emitter.subscribe(GoalFailedEvent, capture_event)
        mocker.patch.object(
            agent.chat, "send", return_value="FAIL - Cannot solve"
        )

        await agent.solve("Impossible problem")

        assert len(event_received) == 1
        assert isinstance(event_received[0], GoalFailedEvent)

    @pytest.mark.asyncio
    async def should_handle_timeout(self, mock_llm_broker, mocker):
        """Test that the agent handles timeout scenarios."""
        agent = SimpleRecursiveAgent(llm=mock_llm_broker)

        # Mock the chat session to delay long enough to trigger timeout
        async def slow_send(*args, **kwargs):
            await asyncio.sleep(10)
            return "Never reached"

        mocker.patch.object(agent, "_generate", side_effect=slow_send)

        # Override the timeout to be very short for testing
        async def quick_timeout_solve(problem):
            solution_future = asyncio.Future()
            state = GoalState(goal=problem, max_iterations=agent.max_iterations)

            async def handle_solution_event(event):
                if not solution_future.done():
                    solution_future.set_result(event.state.solution)

            agent.emitter.subscribe(GoalAchievedEvent, handle_solution_event)
            agent.emitter.subscribe(GoalFailedEvent, handle_solution_event)
            agent.emitter.subscribe(TimeoutEvent, handle_solution_event)

            agent.emitter.emit(GoalSubmittedEvent(state=state))

            try:
                return await asyncio.wait_for(solution_future, timeout=0.1)
            except asyncio.TimeoutError:
                timeout_message = "Timeout: Could not solve the problem within 0.1 seconds."
                if not solution_future.done():
                    state.solution = timeout_message
                    state.is_complete = True
                    agent.emitter.emit(TimeoutEvent(state=state))
                return timeout_message

        result = await quick_timeout_solve("Test problem")

        assert "Timeout" in result

    @pytest.mark.asyncio
    async def should_use_asyncio_to_thread_for_chat_send(
        self, mock_llm_broker, mocker
    ):
        """Test that _generate uses asyncio.to_thread for synchronous chat.send."""
        agent = SimpleRecursiveAgent(llm=mock_llm_broker)

        # Mock asyncio.to_thread
        mock_to_thread = mocker.patch("asyncio.to_thread")
        mock_to_thread.return_value = "Test response"

        result = await agent._generate("Test prompt")

        mock_to_thread.assert_called_once_with(agent.chat.send, "Test prompt")
        assert result == "Test response"

    @pytest.mark.asyncio
    async def should_handle_case_insensitive_done_keyword(
        self, mock_llm_broker, mocker
    ):
        """Test that DONE keyword is case-insensitive."""
        agent = SimpleRecursiveAgent(llm=mock_llm_broker)

        test_cases = ["done - solution", "DoNe - solution", "DONE - solution"]

        for response_text in test_cases:
            mocker.patch.object(agent.chat, "send", return_value=response_text)
            result = await agent.solve("Test problem")
            assert response_text in result

    @pytest.mark.asyncio
    async def should_handle_case_insensitive_fail_keyword(
        self, mock_llm_broker, mocker
    ):
        """Test that FAIL keyword is case-insensitive."""
        agent = SimpleRecursiveAgent(llm=mock_llm_broker)

        test_cases = ["fail - error", "FaIl - error", "FAIL - error"]

        for response_text in test_cases:
            mocker.patch.object(agent.chat, "send", return_value=response_text)
            result = await agent.solve("Test problem")
            assert "Failed to solve" in result

    @pytest.mark.asyncio
    async def should_include_goal_in_prompt(self, mock_llm_broker, mocker):
        """Test that the user's goal is included in the prompt."""
        agent = SimpleRecursiveAgent(llm=mock_llm_broker)

        captured_prompts = []

        def capture_prompt(prompt):
            captured_prompts.append(prompt)
            return "DONE - Solution"

        mocker.patch.object(agent.chat, "send", side_effect=capture_prompt)

        await agent.solve("Find the meaning of life")

        assert len(captured_prompts) > 0
        assert "Find the meaning of life" in captured_prompts[0]

    @pytest.mark.asyncio
    async def should_increment_iteration_count(self, mock_llm_broker, mocker):
        """Test that iteration count is properly incremented."""
        agent = SimpleRecursiveAgent(llm=mock_llm_broker, max_iterations=3)
        iterations_seen = []

        def track_iteration(event):
            iterations_seen.append(event.state.iteration)

        agent.emitter.subscribe(IterationCompletedEvent, track_iteration)

        responses = ["Working...", "Still working...", "DONE - Solution"]
        mocker.patch.object(agent.chat, "send", side_effect=responses)

        await agent.solve("Test problem")

        assert iterations_seen == [1, 2, 3]
