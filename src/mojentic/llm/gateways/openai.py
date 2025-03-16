import json

import structlog
from openai import OpenAI

from mojentic.llm.gateways.llm_gateway import LLMGateway
from mojentic.llm.gateways.models import LLMToolCall, LLMGatewayResponse
from mojentic.llm.gateways.openai_messages_adapter import adapt_messages_to_openai

logger = structlog.get_logger()


class OpenAIGateway(LLMGateway):
    """
    This class is a gateway to the OpenAI LLM service.

    Parameters
    ----------
    api_key : str
        The OpenAI API key to use.
    """

    def __init__(self, api_key):
        self.client = OpenAI(api_key=api_key)

    def complete(self, **args) -> LLMGatewayResponse:
        """
        Complete the LLM request by delegating to the OpenAI service.

        Parameters
        ----------
        model : str
            The name of the model to use, as appears in `ollama list`.
        messages : List[LLMMessage]
            A list of messages to send to the LLM.
        object_model : Optional[BaseModel]
            The model to use for validating the response.
        tools : Optional[List[LLMTool]]
            A list of tools to use with the LLM. If a tool call is requested, the tool will be called and the output
            will be included in the response.
        temperature : float, optional
            The temperature to use for the response. Defaults to 1.0.
        num_ctx : int, optional
            The number of context tokens to use. Defaults to 32768.
        num_predict : int, optional
            The number of tokens to predict. Defaults to no limit.

        Returns
        -------
        LLMGatewayResponse
            The response from the OpenAI service.
        """
        openai_args = {
            'model': args['model'],
            'messages': adapt_messages_to_openai(args['messages']),
        }

        completion = self.client.chat.completions.create

        if 'object_model' in args and args['object_model'] is not None:
            completion = self.client.beta.chat.completions.parse
            openai_args['response_format'] = args['object_model']

        if 'tools' in args and args['tools'] is not None:
            openai_args['tools'] = [t.descriptor for t in args['tools']]

        response = completion(**openai_args)

        object = None
        tool_calls = []

        if 'object_model' in args and args['object_model'] is not None:
            try:
                response_content = response.choices[0].message.content
                object = args['object_model'].model_validate_json(response_content)
            except Exception as e:
                logger.error("Failed to validate model", error=str(e), response=response_content,
                           object_model=args['object_model'])

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

    def get_available_models(self) -> list[str]:
        return [m.id for m in self.client.models.list()]
