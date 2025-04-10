from typing import List

import structlog
from anthropic import Anthropic

from mojentic.llm.gateways import LLMGateway
from mojentic.llm.gateways.models import LLMGatewayResponse, LLMToolCall, MessageRole
from mojentic.llm.gateways.anthropic_messages_adapter import adapt_messages_to_anthropic

logger = structlog.get_logger()

class AnthropicGateway(LLMGateway):
    def __init__(self, api_key: str):
        self.client = Anthropic(api_key=api_key)

    def complete(self, **args) -> LLMGatewayResponse:

        messages = args.get('messages')

        system_messages = [m for m in messages if m.role == MessageRole.System]
        user_messages = [m for m in messages if m.role == MessageRole.User]

        anthropic_args = {
            'model': args['model'],
            'system': " " . join([m.content for m in system_messages]) if system_messages else None,
            'messages': adapt_messages_to_anthropic(user_messages),
        }

        response = self.client.messages.create(
            **anthropic_args,
            temperature=args.get('temperature', 1.0),
            max_tokens=args.get('num_predict', 2000),
            # thinking={
            #     "type": "enabled",
            #     "budget_tokens": 32768,
            # }
        )

        object = None
        tool_calls: List[LLMToolCall] = []

        return LLMGatewayResponse(
            content=response.content[0].text,
            object=object,
            tool_calls=tool_calls,
        )

    def get_available_models(self) -> List[str]:
        return sorted([m.id for m in self.client.models.list()])

    def calculate_embeddings(self, text: str, model: str = "voyage-3-large") -> List[float]:
        raise NotImplementedError("The Anthropic API does not support embedding generation.")
