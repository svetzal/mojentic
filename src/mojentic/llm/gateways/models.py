from enum import Enum
from typing import Optional, List, Union, Annotated, Literal

from pydantic import BaseModel, Field


class MessageRole(Enum):
    """
    The role of the message in the conversation.
    """
    System = 'system'
    User = 'user'
    Assistant = 'assistant'
    Tool = 'tool'


class Annotations(BaseModel):
    audience: list[MessageRole] | None = None
    priority: Annotated[float, Field(ge=0.0, le=1.0)] | None = None


class TextContent(BaseModel):
    """Text content for a message."""

    type: Literal["text"]
    text: str
    """The text content of the message."""
    annotations: Annotations | None = None


class ImageContent(BaseModel):
    """Image content for a message."""

    type: Literal["image"]
    data: str
    """The base64-encoded image data."""
    mimeType: str
    """
    The MIME type of the image. Different providers may support different
    image types.
    """
    annotations: Annotations | None = None


class LLMToolCall(BaseModel):
    """
    A tool call to be made available to the LLM.

    Attributes
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

    Attributes
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

    Attributes
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
