import structlog
from ollama import Options, ChatResponse, chat

from mojentic.llm.gateways.llm_gateway import LLMGateway

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

    def complete(self, **args):
        logger.info("Delegating to Ollama for completion", **args)

        options = self._extract_options_from_args(args)

        ollama_args = {
            'model': args['model'],
            'messages': args['messages'],
            'options': options
        }

        if 'response_model' in args and args['response_model'] is not None:
            ollama_args['format'] = args['response_model'].model_json_schema()

        if 'tools' in args:
            ollama_args['tools'] = [t['descriptor'] for t in args['tools']]

        response: ChatResponse = chat(**ollama_args)

        object = None
        if 'response_model' in args:
            try:
                object = args['response_model'].model_validate_json(response.message.content)
            except Exception as e:
                logger.error("Failed to validate model in", error=str(e), response=response.message.content,
                             response_model=args['response_model'])

        return {
            'content': response.message.content,
            'object': object,
            'tool_calls': response.message.tool_calls
        }
