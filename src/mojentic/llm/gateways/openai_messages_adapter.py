import base64
import json
import os
from typing import List, Any

import structlog

from mojentic.llm.gateways.models import LLMMessage, MessageRole

logger = structlog.get_logger()


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
                        with open(image_path, "rb") as image_file:
                            base64_image = base64.b64encode(image_file.read()).decode('utf-8')

                            # Determine image type from file extension
                            _, ext = os.path.splitext(image_path)
                            image_type = ext.lstrip('.').lower()
                            if image_type not in ['jpeg', 'jpg', 'png', 'gif', 'webp']:
                                image_type = 'jpeg'  # Default to jpeg if unknown extension

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
