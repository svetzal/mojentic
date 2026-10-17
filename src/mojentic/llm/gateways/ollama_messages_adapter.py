import structlog

from mojentic.llm.gateways.models import LLMMessage, MessageRole

logger = structlog.get_logger()


def adapt_messages_to_ollama(messages: list[LLMMessage]):
    new_messages: list[dict[str, str]] = []
    for m in messages:
        if m.role == MessageRole.System:
            new_messages.append({"role": "system", "content": m.content})
        elif m.role == MessageRole.User:
            msg = {"role": "user", "content": m.content}
            if m.image_paths is not None:
                msg["images"] = m.image_paths
            new_messages.append(msg)
        elif m.role == MessageRole.Assistant:
            msg = {"role": "assistant", "content": m.content or ""}
            if m.thinking is not None:
                msg["thinking"] = m.thinking
            if m.tool_calls is not None:
                msg["tool_calls"] = [
                    {
                        **({"id": call.id} if call.id is not None else {}),
                        "type": "function",
                        "function": {"name": call.name, "arguments": call.arguments},
                    }
                    for call in m.tool_calls
                ]
            new_messages.append(msg)
        elif m.role == MessageRole.Tool:
            new_messages.append(
                {
                    "role": "tool",
                    "content": m.content,
                }
            )
        else:
            logger.error("Unknown message role", role=m.role)
    return new_messages
