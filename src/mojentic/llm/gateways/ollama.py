from typing import List, Iterator
import structlog
from ollama import Client, Options, ChatResponse
from pydantic import BaseModel

from mojentic.llm.gateways.llm_gateway import LLMGateway
from mojentic.llm.gateways.models import LLMToolCall, LLMGatewayResponse
from mojentic.llm.gateways.ollama_messages_adapter import adapt_messages_to_ollama

logger = structlog.get_logger()

class StreamingResponse(BaseModel):
    """Simple wrapper for streaming response content"""
    content: str

class OllamaGateway(LLMGateway):
    """
    This class is a gateway to the Ollama LLM service.

    Parameters
    ----------
    host : str, optional
        The Ollama host to connect to. Defaults to "http://localhost:11434".
    headers : dict, optional
        The headers to send with the request. Defaults to an empty dict.
    """

    def __init__(self, host="http://localhost:11434", headers={}, timeout=None):
        self.client = Client(host=host, headers=headers, timeout=timeout)

    def _extract_options_from_args(self, args):
        options = Options(
            temperature=args.get('temperature', 1.0),
            num_ctx=args.get('num_ctx', 32768),
        )
        if args.get('num_predict', 0) > 0:
            options.num_predict = args['num_predict']
        return options

    def complete(self, **args) -> LLMGatewayResponse:
        """
        Complete the LLM request by delegating to the Ollama service.

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
            The response from the Ollama service.
        """
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
            ollama_args['tools'] = [t.descriptor for t in args['tools']]

        response: ChatResponse = self.client.chat(**ollama_args)

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

    def complete_stream(self, **args) -> Iterator[StreamingResponse]:
        """
        Stream the LLM response from Ollama service.

        Parameters
        ----------
        model : str
            The name of the model to use, as appears in `ollama list`.
        messages : List[LLMMessage]
            A list of messages to send to the LLM.
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
        Iterator[StreamingResponse]
            An iterator of StreamingResponse objects containing response chunks.
        """
        logger.info("Delegating to Ollama for streaming completion", **args)

        options = self._extract_options_from_args(args)
        ollama_args = {
            'model': args['model'],
            'messages': adapt_messages_to_ollama(args['messages']),
            'options': options,
            'stream': True
        }

        #
        # This is here 2025-02-21 to demonstrate a deficiency in Ollama tool calling
        # using the Stream option. We can't get chunk by chunk responses from the LLM
        # when using tools. This limits our ability to explore streaming capabilities
        # in the mojentic API, so I'm pausing this work for now until this is resolved.
        # https://github.com/ollama/ollama/issues/7886
        #

        # if 'tools' in args and args['tools'] is not None:
        #     ollama_args['tools'] = [t.descriptor for t in args['tools']]

        stream = self.client.chat(**ollama_args)

        for chunk in stream:
            if chunk.message:
                if chunk.message.content:
                    yield StreamingResponse(content=chunk.message.content)
                # if chunk.message.tool_calls:
                #     for tool_call in chunk.message.tool_calls:
                #         yield StreamingResponse(
                #             content=f"\nTOOL CALL: {tool_call.function.name}({tool_call.function.arguments})\n"
                #         )

    def get_available_models(self) -> List[str]:
        """
        Get the list of available local models.

        Returns
        -------
        List[str]
            The list of available models.
        """
        return [m.model for m in self.client.list().models]

    def pull_model(self, model: str) -> None:
        """
        Pull the model from the Ollama service.

        Parameters
        ----------
        model : str
            The name of the model to pull.
        """
        self.client.pull(model)
