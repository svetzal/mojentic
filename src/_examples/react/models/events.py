from pydantic import Field

from mojentic import Event
from .base import CurrentContext, NextAction


class InvokeThinking(Event):
    context: CurrentContext = Field(..., description="The current context as we work through our response.")


class InvokeDecisioning(Event):
    context: CurrentContext = Field(..., description="The current context as we work through our response.")


class InvokeToolCall(Event):
    context: CurrentContext = Field(..., description="The current context as we work through our response.")
    thought: str = Field(..., description="The reasoning behind the decision.")
    action: NextAction


class FinishAndSummarize(Event):
    context: CurrentContext = Field(..., description="The current context as we work through our response.")
    thought: str = Field(..., description="The reasoning behind the decision.")


class FailureOccurred(Event):
    context: CurrentContext = Field(..., description="The current context as we work through our response.")
    reason: str = Field(..., description="The reason for the failure.")