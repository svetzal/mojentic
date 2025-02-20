from enum import Enum
from typing import List

from pydantic import Field, BaseModel


class NextAction(str, Enum):
    PLAN = "PLAN"
    ACT = "ACT"
    FINISH = "FINISH"


class ThoughtActionObservation(BaseModel):
    thought: str = Field(..., description="The thought process behind the action taken in the current context.")
    action: str = Field(..., description="The action taken in the current context.")
    observation: str = Field(..., description="The observation made after the action taken in the current context.")


class Plan(BaseModel):
    steps: List[str] = Field([],
                            description="How to answer the query, step by step, each step outlining an action to take.")


class CurrentContext(BaseModel):
    user_query: str = Field(..., description="The user query to which we are responding.")
    plan: Plan = Field(Plan(steps=[]), description="The current plan of action for the current context.")
    history: List[ThoughtActionObservation] = Field([],
                                                   description="The history of actions taken and observations made in the current context.")
    iteration: int = Field(0, description="The number of iterations taken in the current context.")