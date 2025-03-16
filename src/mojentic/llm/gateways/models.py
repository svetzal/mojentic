from enum import Enum
from typing import Optional, List, Union

from pydantic import BaseModel, Field


class MessageRole(Enum):
    """
    The role of the message in the conversation.
    """
    System = 'system'
    User = 'user'
    Assistant = 'assistant'
    Tool = 'tool'


class LLMToolCall(BaseModel):
    """
    A tool call to be made available to the LLM.

    Parameters
    ----------
    id : Optional[str]
        The identifier of the tool call.
    name : str
        The name of the tool call.
    arguments : dict[str, str]
        The arguments for the tool call.
    """
    id: Optional[str] = None
    name: str
    arguments: dict[str, str]


class LLMMessage(BaseModel):
    """
    A message to be sent to the LLM. These would accumulate during a chat session with an LLM.

    Parameters
    ----------
    role : MessageRole
        The role of the message in the conversation.
    content : Optional[str]
        The content of the message.
    object : Optional[BaseModel]
        The object representation of the message.
    tool_calls : Optional[List[LLMToolCall]]
        A list of tool calls to be made available to the LLM.
    image_paths : Optional[List[str]]
        A list of file paths to images to be included with the message.
        Note: You must use an image-capable model to process images.
    """
    role: MessageRole = MessageRole.User
    content: Optional[str] = None
    object: Optional[BaseModel] = None
    tool_calls: Optional[List[LLMToolCall]] = None
    image_paths: Optional[List[str]] = None


class LLMGatewayResponse(BaseModel):
    """
    The response from the LLM gateway, abstracting you from the quirks of a specific LLM.

    Parameters
    ----------
    content : Optional[Union[str, dict[str, str]]]
        The content of the response.
    object : Optional[BaseModel]
        Parsed response object.
    tool_calls : List[LLMToolCall]
        List of requested tool calls from the LLM.
    """
    content: Optional[Union[str, dict[str, str]]] = Field(None, description="The content of the response.")
    object: Optional[BaseModel] = Field(None, description="Parsed response object")
    tool_calls: List[LLMToolCall] = Field(default_factory=list,
                                          description="List of requested tool calls from the LLM.")
