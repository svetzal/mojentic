import structlog
from ollama import ChatResponse, chat, Options
from openai import OpenAI

logger = structlog.get_logger()


class LLMGateway:
    def complete(self, **args):
        raise NotImplementedError

    def complete_with_object(self, **args):
        raise NotImplementedError


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
        logger.info("Delegating to Ollama for text completion", **args)

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

        if 'response_model' in args:
            try:
                content = args['response_model'].model_validate_json(response.message.content)
            except Exception as e:
                logger.error("Failed to validate model in", error=str(e), response=response.message.content, response_model=args['response_model'])
                content = response.message.content
        else:
            content = response.message.content

        return {
            'content': content,
            'tool_calls': response.message.tool_calls
        }

    def complete_with_object(self, **args):
        logger.info("Delegating to Ollama for model completion", **args)

        options = self._extract_options_from_args(args)

        ollama_args = {
            'model': args['model'],
            'messages': args['messages'],
            'options': options,
            'format': args['response_model'].model_json_schema()
        }

        response: ChatResponse = chat(**ollama_args)
        return args['response_model'].model_validate_json(response.message.content)


class OpenAIGateway(LLMGateway):
    def __init__(self, api_key):
        self.client = OpenAI(api_key=api_key)

    def complete(self, **args):
        response = self.client.chat.completions.create(
            model=args['model'],
            messages=args['messages'],
            # max_tokens=num_predict,
        )

        return {
            'content': response.choices[0].message.content,
        }

    def complete_with_object(self, **args):
        response = self.client.beta.chat.completions.parse(
            model=args['model'],
            messages=args['messages'],
            # max_tokens=num_predict,
            response_format=args['response_model'],
        )

        return response.choices[0].message.parsed
