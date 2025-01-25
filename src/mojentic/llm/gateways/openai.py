import structlog
from openai import OpenAI

from mojentic.llm.gateways.llm_gateway import LLMGateway

logger = structlog.get_logger()


class OpenAIGateway(LLMGateway):
    def __init__(self, api_key):
        self.client = OpenAI(api_key=api_key)

    def complete(self, **args):
        openai_args = {
            'model': args['model'],
            'messages': args['messages'],
        }

        if 'response_model' in args and args['response_model'] is not None:
            openai_args['response_format'] = args['response_model']
            response = self.client.beta.chat.completions.parse(**openai_args)
            return {
                'content': response.choices[0].message.content,
                'model': response.choices[0].message.parsed,
            }
        else:
            response = self.client.chat.completions.create(**openai_args)
            return {
                'content': response.choices[0].message.content,
            }
