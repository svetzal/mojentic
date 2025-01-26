from enum import Enum
from typing import Optional, List, Union

from pydantic import BaseModel, Field


class MessageRole(Enum):
    System = 'system'
    User = 'user'
    Assistant = 'assistant'
    Tool = 'tool'


class LLMToolCall(BaseModel):
    id: Optional[str] = None
    name: str
    arguments: dict[str, str]


class LLMMessage(BaseModel):
    role: MessageRole = MessageRole.User
    content: Optional[Union[str, dict[str,str]]] = None
    object: Optional[BaseModel] = None
    tool_calls: Optional[List[LLMToolCall]] = None


class LLMGatewayResponse(BaseModel):
    content: Optional[Union[str, dict[str,str]]] = Field(None, description="The content of the response.")
    object: Optional[BaseModel] = Field(None, description="Parsed response object")
    tool_calls: List[LLMToolCall] = Field(default_factory=list,
                                          description="List of requested tool calls from the llm.")
