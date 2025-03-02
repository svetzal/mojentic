from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field

from mojentic.llm.gateways.models import LLMMessage


class PotentialAction(BaseModel):
    action: str = Field(..., description="The action to be taken")
    reasoning: str = Field(..., description="The reasoning behind the action, why it should be chosen")


class Action(BaseModel):
    action: str = Field(..., description="The action to be taken")
    reasoning: str = Field(..., description="The reasoning behind the action, why it should be chosen")
    context: str = Field(..., description="The observations at the time the action was taken")
    started_at: datetime = Field(..., description="When the action was started")
    result: Optional[str] = Field(None, description="The result of the action")
    tool_calls: Optional[List[LLMMessage]] = Field(None, description="The tools used to complete the action, and their outputs")


class PotentialActions(BaseModel):
    list: List[PotentialAction] = Field(..., description="List of potential actions")
