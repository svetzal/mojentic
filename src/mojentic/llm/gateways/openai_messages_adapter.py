import json
from typing import List

import structlog

from mojentic.llm.gateways.models import LLMMessage, MessageRole

logger = structlog.get_logger()


def adapt_messages_to_openai(messages: List[LLMMessage]):
    new_messages: List[dict[str, str]] = []
    for m in messages:
        if m.role == MessageRole.System:
            new_messages.append({'role': 'system', 'content': m.content})
        elif m.role == MessageRole.User:
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
