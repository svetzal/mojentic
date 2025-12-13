"""Event definitions for the ReAct pattern.

This module defines all event types used to coordinate the ReAct loop,
including thinking, decisioning, tool calls, completion, and failure events.
"""
from pydantic import Field

from mojentic import Event

from .base import CurrentContext, NextAction


class InvokeThinking(Event):
    """Event to trigger the thinking/planning phase.

    This event initiates the planning process where the agent creates
    or refines a plan for answering the user's query.
    """

    context: CurrentContext = Field(
        ...,
        description="The current context as we work through our response."
    )


class InvokeDecisioning(Event):
    """Event to trigger the decision-making phase.

    This event initiates the decision process where the agent evaluates
    the current plan and history to decide on the next action.
    """

    context: CurrentContext = Field(
        ...,
        description="The current context as we work through our response."
    )


class InvokeToolCall(Event):
    """Event to trigger a tool invocation.

    This event carries the information needed to execute a specific tool
    with given arguments, along with the reasoning behind the decision.
    """

    context: CurrentContext = Field(
        ...,
        description="The current context as we work through our response."
    )
    thought: str = Field(
        ...,
        description="The reasoning behind the decision."
    )
    action: NextAction
    tool: object = Field(
        ...,
        description="The tool instance to invoke."
    )
    tool_arguments: dict = Field(
        default_factory=dict,
        description="Arguments to pass to the tool."
    )


class FinishAndSummarize(Event):
    """Event to trigger the completion and summarization phase.

    This event indicates that the agent has gathered sufficient information
    to answer the user's query and should generate a final response.
    """

    context: CurrentContext = Field(
        ...,
        description="The current context as we work through our response."
    )
    thought: str = Field(
        ...,
        description="The reasoning behind the decision."
    )


class FailureOccurred(Event):
    """Event to signal a failure in the ReAct loop.

    This event captures errors or unrecoverable situations that prevent
    the agent from continuing to process the user's query.
    """

    context: CurrentContext = Field(
        ...,
        description="The current context as we work through our response."
    )
    reason: str = Field(
        ...,
        description="The reason for the failure."
    )
