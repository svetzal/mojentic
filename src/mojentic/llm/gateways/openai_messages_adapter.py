import base64
import json
import os
from typing import List, Any

import structlog

from mojentic.llm.gateways.models import LLMMessage, MessageRole

logger = structlog.get_logger()


def read_file_as_binary(file_path: str) -> bytes:
    """Read a file as binary data.

    This function encapsulates the external library call to open() so it can be mocked in tests.

    Args:
        file_path: Path to the file to read

    Returns:
        Binary content of the file
    """
    with open(file_path, "rb") as file:
        return file.read()


def encode_base64(data: bytes) -> str:
    """Encode binary data as base64 string.

    This function encapsulates the external library call to base64.b64encode() so it can be mocked in tests.

    Args:
        data: Binary data to encode

    Returns:
        Base64-encoded string
    """
    return base64.b64encode(data).decode('utf-8')


def get_image_type(file_path: str) -> str:
    """Determine image type from file extension.

    This function encapsulates the external library call to os.path.splitext() so it can be mocked in tests.

    Args:
        file_path: Path to the image file

    Returns:
        Image type (e.g., 'jpeg', 'png')
    """
    _, ext = os.path.splitext(file_path)
    image_type = ext.lstrip('.').lower()

    # Convert 'jpg' to 'jpeg'
    if image_type == 'jpg':
        return 'jpeg'

    # Use 'jpeg' for unknown extensions, otherwise use the detected type
    return image_type if image_type in ['jpeg', 'png', 'gif', 'webp'] else 'jpeg'


def adapt_messages_to_openai(messages: List[LLMMessage]):
    new_messages: List[dict[str, Any]] = []
    for m in messages:
        if m.role == MessageRole.System:
            new_messages.append({'role': 'system', 'content': m.content})
        elif m.role == MessageRole.User:
            if m.image_paths is not None and len(m.image_paths) > 0:
                # Create a content structure with text and images
                content = []
                if m.content:
                    content.append({"type": "text", "text": m.content})

                # Add each image as a base64-encoded URL
                for image_path in m.image_paths:
                    try:
                        # Use our encapsulated methods instead of direct library calls
                        binary_data = read_file_as_binary(image_path)
                        base64_image = encode_base64(binary_data)
                        image_type = get_image_type(image_path)

                        content.append({
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/{image_type};base64,{base64_image}"
                            }
                        })
                    except Exception as e:
                        logger.error("Failed to encode image", error=str(e), image_path=image_path)

                new_messages.append({'role': 'user', 'content': content})
            else:
                new_messages.append({'role': 'user', 'content': m.content})
        elif m.role == MessageRole.Assistant:
            msg = {'role': 'assistant', 'content': m.content or ''}
            if m.tool_calls is not None:
                msg['tool_calls'] = [{
                    'id': m.tool_calls[0].id,
                    'type': 'function',
                    'function': {
                        'name': m.tool_calls[0].name,
                        'arguments': json.dumps({k: v for k, v in m.tool_calls[0].arguments.items()})
                    }
                }]
            new_messages.append(msg)
        elif m.role == MessageRole.Tool:
            new_messages.append({
                'role': 'tool',
                'content': m.content,
                'tool_call_id': m.tool_calls[0].id
            })
        else:
            logger.error("Unknown message role", role=m.role)
    return new_messages
