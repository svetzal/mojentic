import structlog
from ollama import Options, ChatResponse, chat

from mojentic.llm.gateways.llm_gateway import LLMGateway
from mojentic.llm.gateways.models import LLMToolCall, LLMGatewayResponse
from mojentic.llm.gateways.ollama_messages_adapter import adapt_messages_to_ollama

logger = structlog.get_logger()


class OllamaGateway(LLMGateway):
    def _extract_options_from_args(self, args):
        options = Options(
            temperature=args['temperature'],
            num_ctx=args['num_ctx']
        )
        if args['num_predict'] > 0:
            options.num_predict = args['num_predict']
        return options

    def complete(self, **args) -> LLMGatewayResponse:
        logger.info("Delegating to Ollama for completion", **args)

        options = self._extract_options_from_args(args)

        ollama_args = {
            'model': args['model'],
            'messages': adapt_messages_to_ollama(args['messages']),
            'options': options
        }

        if 'object_model' in args and args['object_model'] is not None:
            ollama_args['format'] = args['object_model'].model_json_schema()

        if 'tools' in args and args['tools'] is not None:
            ollama_args['tools'] = [t['descriptor'] for t in args['tools']]

        response: ChatResponse = chat(**ollama_args)

        object = None
        tool_calls = []

        if 'object_model' in args:
            try:
                object = args['object_model'].model_validate_json(response.message.content)
            except Exception as e:
                logger.error("Failed to validate model in", error=str(e), response=response.message.content,
                             object_model=args['object_model'])

        if response.message.tool_calls is not None:
            tool_calls = [LLMToolCall(name=t.function.name,
                                      arguments={str(k): str(t.function.arguments[k]) for k in t.function.arguments})
                          for t in response.message.tool_calls]

        return LLMGatewayResponse(
            content=response.message.content,
            object=object,
            tool_calls=tool_calls,
        )
