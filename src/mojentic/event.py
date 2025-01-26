from typing import Optional

from pydantic import BaseModel, Field


class Event(BaseModel):
    source: type = Field(..., title="The type of the agent that created the event.")
    correlation_id: Optional[str] = Field(None, title="The unique identifier for a series or chain of events.")


class TerminateEvent(Event):
    pass
