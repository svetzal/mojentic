import json

import structlog
from openai import OpenAI

from mojentic.llm.gateways.llm_gateway import LLMGateway
from mojentic.llm.gateways.models import LLMToolCall, LLMGatewayResponse
from mojentic.llm.gateways.openai_messages_adapter import adapt_messages_to_openai

logger = structlog.get_logger()


class OpenAIGateway(LLMGateway):
    def __init__(self, api_key):
        self.client = OpenAI(api_key=api_key)

    def complete(self, **args) -> LLMGatewayResponse:
        openai_args = {
            'model': args['model'],
            'messages': adapt_messages_to_openai(args['messages']),
        }

        completion = self.client.chat.completions.create

        if 'object_model' in args and args['object_model'] is not None:
            openai_args['response_format'] = args['object_model']
            completion = self.client.beta.chat.completions.parse

        if 'tools' in args and args['tools'] is not None:
            openai_args['tools'] = [t.descriptor for t in args['tools']]

        response = completion(**openai_args)

        object = None
        tool_calls = []

        if 'object_model' in args and args['object_model'] is not None:
            object = response.choices[0].message.parsed

        if response.choices[0].message.tool_calls is not None:
            for t in response.choices[0].message.tool_calls:
                arguments = {}
                args_dict = json.loads(t.function.arguments)
                for k in args_dict:
                    arguments[str(k)] = str(args_dict[k])
                tool_call = LLMToolCall(id=t.id, name=t.function.name, arguments=arguments)
                tool_calls.append(tool_call)

        return LLMGatewayResponse(
            content=response.choices[0].message.content,
            object=object,
            tool_calls=tool_calls,
        )
