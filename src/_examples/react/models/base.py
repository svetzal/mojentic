"""Base data models for the ReAct pattern.

This module defines the core data structures used throughout the ReAct
implementation, including actions, plans, observations, and context.
"""
from enum import Enum
from typing import List

from pydantic import BaseModel, Field


class NextAction(str, Enum):
    """Enumeration of possible next actions in the ReAct loop."""

    PLAN = "PLAN"
    ACT = "ACT"
    FINISH = "FINISH"


class ThoughtActionObservation(BaseModel):
    """A single step in the ReAct loop capturing thought, action, and observation.

    This model represents one iteration of the ReAct pattern where the agent:
    1. Thinks about what to do
    2. Takes an action
    3. Observes the result
    """

    thought: str = Field(
        ...,
        description="The thought process behind the action taken in the current context."
    )
    action: str = Field(
        ...,
        description="The action taken in the current context."
    )
    observation: str = Field(
        ...,
        description="The observation made after the action taken in the current context."
    )


class Plan(BaseModel):
    """A structured plan for solving a user query.

    Contains a list of steps that outline how to approach answering the query.
    """

    steps: List[str] = Field(
        [],
        description="How to answer the query, step by step, each step outlining an action to take."
    )


class CurrentContext(BaseModel):
    """The complete context for a ReAct session.

    This model tracks everything needed to maintain state throughout the
    reasoning and acting loop, including the user's query, the plan,
    the history of actions, and the iteration count.
    """

    user_query: str = Field(
        ...,
        description="The user query to which we are responding."
    )
    plan: Plan = Field(
        Plan(steps=[]),
        description="The current plan of action for the current context."
    )
    history: List[ThoughtActionObservation] = Field(
        [],
        description="The history of actions taken and observations made in the current context."
    )
    iteration: int = Field(
        0,
        description="The number of iterations taken in the current context."
    )
