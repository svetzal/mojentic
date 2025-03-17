"""
A simple declarative agent implementation that leverages events and async.
This implementation provides a more declarative approach to problem-solving.
"""

import asyncio
from typing import List, Optional

from pydantic import BaseModel

from mojentic.llm.gateways.models import LLMMessage
from mojentic.llm.llm_broker import LLMBroker
from mojentic.llm.tools.llm_tool import LLMTool
from mojentic.llm.chat_session import ChatSession


class ProblemState(BaseModel):
    """
    Represents the state of a problem-solving process.
    """
    problem: str
    iteration: int = 0
    max_iterations: int = 5
    solution: Optional[str] = None
    is_complete: bool = False


class SolverEvent(BaseModel):
    """
    Base class for solver events.
    """
    state: ProblemState


class ProblemSubmittedEvent(SolverEvent):
    """
    Event triggered when a problem is submitted for solving.
    """
    pass


class IterationCompletedEvent(SolverEvent):
    """
    Event triggered when an iteration of the problem-solving process is completed.
    """
    response: str


class ProblemSolvedEvent(SolverEvent):
    """
    Event triggered when a problem is solved.
    """
    pass


class ProblemFailedEvent(SolverEvent):
    """
    Event triggered when a problem cannot be solved.
    """
    pass


class TimeoutEvent(SolverEvent):
    """
    Event triggered when the problem-solving process times out.
    """
    pass


class EventEmitter:
    """
    A simple event emitter that allows subscribing to and emitting events.
    """

    def __init__(self):
        self.subscribers = {}

    def subscribe(self, event_type, callback):
        """
        Subscribe to an event type.

        Parameters
        ----------
        event_type : type
            The type of event to subscribe to
        callback : callable
            The callback function to be called when an event of the specified type is emitted

        Returns
        -------
        callable
            A function that can be called to unsubscribe from the event
        """
        if event_type not in self.subscribers:
            self.subscribers[event_type] = []
        self.subscribers[event_type].append(callback)
        return lambda: self.subscribers[event_type].remove(callback)  # Return unsubscribe function

    def emit(self, event):
        """
        Emit an event to all subscribers.

        Parameters
        ----------
        event : Event
            The event to emit to subscribers
        """
        event_type = type(event)
        if event_type in self.subscribers:
            for callback in self.subscribers[event_type]:
                result = callback(event)
                # If the callback is a coroutine, create a task for it
                if asyncio.iscoroutine(result):
                    asyncio.create_task(result)


class SimpleRecursiveAgent:
    """An agent that recursively attempts to solve a problem using available tools.

    This agent uses an event-driven approach to manage the problem-solving process.
    It will continue attempting to solve the problem until it either succeeds,
    fails explicitly, or reaches the maximum number of recursions.

    Attributes
    ----------
    max_iterations : int
        The maximum number of iterations to perform
    llm : LLMBroker
        The language model broker to use for generating responses
    emitter : EventEmitter
        The pubsub event emitter used to manage events
    available_tools : List[LLMTool]
        List of tools that can be used to solve the problem
    chat : ChatSession
        The chat session used for problem-solving interaction
    """
    max_iterations: int
    llm: LLMBroker
    available_tools: List[LLMTool]
    emitter: EventEmitter
    chat: ChatSession

    def __init__(self, llm: LLMBroker, available_tools: Optional[List[LLMTool]] = None, max_iterations: int = 5):
        """
        Initialize the SimpleRecursiveAgent.

        Parameters
        ----------
        llm : LLMBroker
            The language model broker to use for generating responses
        max_iterations : int
            The maximum number of iterations to perform
        available_tools : Optional[List[LLMTool]]
            List of tools that can be used to solve the problem
        """
        self.max_iterations = max_iterations
        self.llm = llm
        self.available_tools = available_tools or []
        self.emitter = EventEmitter()

        # Initialize the chat session
        self.chat = ChatSession(
            llm=llm,
            system_prompt="You are a problem-solving assistant that can solve complex problems step by step. "
                         "You analyze problems, break them down into smaller parts, and solve them systematically. "
                         "If you cannot solve a problem completely in one step, you make progress and identify what to do next.",
            tools=self.available_tools
        )

        # Set up event handlers
        self.emitter.subscribe(ProblemSubmittedEvent, self._handle_problem_submitted)
        self.emitter.subscribe(IterationCompletedEvent, self._handle_iteration_completed)

    async def solve(self, problem: str) -> str:
        """
        Solve a problem asynchronously.

        Parameters
        ----------
        problem : str
            The problem to solve

        Returns
        -------
        str
            The solution to the problem
        """
        # Create a future to signal when the solution is ready
        solution_future = asyncio.Future()

        # Create the initial problem state
        state = ProblemState(problem=problem, max_iterations=self.max_iterations)

        # Define handlers for completion events
        async def handle_solution_event(event):
            if not solution_future.done():
                solution_future.set_result(event.state.solution)

        # Subscribe to completion events
        self.emitter.subscribe(ProblemSolvedEvent, handle_solution_event)
        self.emitter.subscribe(ProblemFailedEvent, handle_solution_event)
        self.emitter.subscribe(TimeoutEvent, handle_solution_event)

        # Start the solving process
        self.emitter.emit(ProblemSubmittedEvent(state=state))

        # Wait for the solution or timeout
        try:
            return await asyncio.wait_for(solution_future, timeout=300)  # 5 minutes timeout
        except asyncio.TimeoutError:
            timeout_message = f"Timeout: Could not solve the problem within 300 seconds."
            if not solution_future.done():
                state.solution = timeout_message
                state.is_complete = True
                self.emitter.emit(TimeoutEvent(state=state))
            return timeout_message

    async def _handle_problem_submitted(self, event: ProblemSubmittedEvent):
        """
        Handle a problem submitted event.

        Parameters
        ----------
        event : ProblemSubmittedEvent
            The problem submitted event to handle
        """
        # Start the first iteration
        await self._process_iteration(event.state)

    async def _handle_iteration_completed(self, event: IterationCompletedEvent):
        """
        Handle an iteration completed event.

        Parameters
        ----------
        event : IterationCompletedEvent
            The iteration completed event to handle
        """
        state = event.state
        response = event.response

        # Check if the task failed or succeeded
        if "FAIL".lower() in response.lower():
            state.solution = f"Failed to solve after {state.iteration} iterations:\n{response}"
            state.is_complete = True
            self.emitter.emit(ProblemFailedEvent(state=state))
            return
        elif "DONE".lower() in response.lower():
            state.solution = response
            state.is_complete = True
            self.emitter.emit(ProblemSolvedEvent(state=state))
            return

        # Check if we've reached the maximum number of iterations
        if state.iteration >= state.max_iterations:
            state.solution = f"Best solution after {state.max_iterations} iterations:\n{response}"
            state.is_complete = True
            self.emitter.emit(ProblemSolvedEvent(state=state))
            return

        # If the problem is not solved and we haven't reached max_iterations, continue with next iteration
        await self._process_iteration(state)

    async def _process_iteration(self, state: ProblemState):
        """
        Process a single iteration of the problem-solving process.

        Parameters
        ----------
        state : ProblemState
            The current state of the problem-solving process
        """
        # Increment the iteration counter
        state.iteration += 1

        # Create a prompt for the LLM
        prompt = f"""
Given the user request:
{state.problem}

Use the tools at your disposal to act on their request. You may wish to create a step-by-step plan for more complicated requests.

If you cannot provide an answer, say only "FAIL".
If you have the answer, say only "DONE".
"""

        # Generate a response using the LLM
        response = await self._generate(prompt)

        # Emit an event with the response
        self.emitter.emit(IterationCompletedEvent(state=state, response=response))

    async def _generate(self, prompt: str) -> str:
        """
        Generate a response using the ChatSession asynchronously.

        Parameters
        ----------
        prompt : str
            The prompt to send to the ChatSession

        Returns
        -------
        str
            The generated response
        """
        # Use asyncio.to_thread to run the synchronous send method in a separate thread
        # without blocking the event loop
        return await asyncio.to_thread(self.chat.send, prompt)
