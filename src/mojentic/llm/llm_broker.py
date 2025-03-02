import json
from typing import List, Optional, Type

import structlog
from pydantic import BaseModel

from mojentic.llm.gateways.llm_gateway import LLMGateway
from mojentic.llm.gateways.models import MessageRole, LLMMessage, LLMGatewayResponse
from mojentic.llm.gateways.ollama import OllamaGateway
from mojentic.llm.gateways.tokenizer_gateway import TokenizerGateway

logger = structlog.get_logger()


class LLMBroker():
    """
    This class is responsible for managing interaction with a Large Language Model. It abstracts the user
    from the specific mechanics of the LLM and provides a common interface for generating responses.
    """

    adapter: LLMGateway
    tokenizer: TokenizerGateway
    model: str

    def __init__(self, model: str, gateway: Optional[LLMGateway] = None, tokenizer: Optional[TokenizerGateway] = None):
        """
        Create an instance of the LLMBroker.

        Parameters
        ----------
        model
            The name of the model to use.
        gateway
            The gateway to use for communication with the LLM. If None, a gateway is created that will utilize a local
            Ollama server.
        tokenizer
            The gateway to use for tokenization. This is used to log approximate token counts for the LLM calls. If
            None, `mxbai-embed-large` is used on a local Ollama server.
        """
        self.model = model
        if tokenizer is None:
            self.tokenizer = TokenizerGateway()
        else:
            self.tokenizer = tokenizer
        if gateway is None:
            self.adapter = OllamaGateway()
        else:
            self.adapter = gateway

    def generate(self, messages: List[LLMMessage], tools=None, temperature=1.0, num_ctx=32768, num_predict=-1) -> str:
        """
        Generate a text response from the LLM.

        Parameters
        ----------
        messages : LLMMessage
            A list of messages to send to the LLM.
        tools : List[Tool]
            A list of tools to use with the LLM. If a tool call is requested, the tool will be called and the output
            will be included in the response.
        temperature : float
            The temperature to use for the response. Defaults to 1.0
        num_ctx : int
            The number of context tokens to use. Defaults to 32768.
        num_predict : int
            The number of tokens to predict. Defaults to no limit.

        Returns
        -------
        str
            The response from the LLM.
        """
        approximate_tokens = len(self.tokenizer.encode(self._content_to_count(messages)))
        logger.info(f"Requesting llm response with approx {approximate_tokens} tokens")

        result: LLMGatewayResponse = self.adapter.complete(
            model=self.model,
            messages=messages,
            tools=tools,
            temperature=temperature,
            num_ctx=num_ctx,
            num_predict=num_predict)

        if result.tool_calls and tools is not None:
            logger.info("Tool call requested")
            for tool_call in result.tool_calls:
                if tool := next((t for t in tools if
                                 t.matches(tool_call.name)),
                                None):
                    logger.info('Calling function', function=tool_call.name)
                    logger.info('Arguments:', arguments=tool_call.arguments)
                    output = tool.run(**tool_call.arguments)
                    logger.info('Function output', output=output)
                    messages.append(LLMMessage(role=MessageRole.Assistant, tool_calls=[tool_call]))
                    messages.append(
                        LLMMessage(role=MessageRole.Tool, content=json.dumps(output), tool_calls=[tool_call]))
                    # {'role': 'tool', 'content': str(output), 'name': tool_call.name, 'tool_call_id': tool_call.id})
                    return self.generate(messages, tools, temperature, num_ctx, num_predict)
                else:
                    logger.warn('Function not found', function=tool_call.name)
                    logger.info('Expected usage of missing function', expected_usage=tool_call)
                    # raise Exception('Unknown tool function requested:', requested_tool.function.name)

        return result.content

    def _content_to_count(self, messages: List[LLMMessage]):
        content = ""
        for message in messages:
            if message.content:
                content += message.content
        return content

    def generate_object(self, messages: List[LLMMessage], object_model: Type[BaseModel], temperature=1.0, num_ctx=32768,
                        num_predict=-1) -> BaseModel:
        """
        Generate a structured response from the LLM and return it as an object.

        Parameters
        ----------
        messages : List[LLMMessage]
            A list of messages to send to the LLM.
        object_model : BaseModel
            The class of the model to use for the structured response data.
        temperature : float
            The temperature to use for the response. Defaults to 1.0.
        num_ctx : int
            The number of context tokens to use. Defaults to 32768.
        num_predict : int
            The number of tokens to predict. Defaults to no limit.

        Returns
        -------
        BaseModel
            An instance of the model class provided containing the structured response data.
        """
        approximate_tokens = len(self.tokenizer.encode(self._content_to_count(messages)))
        logger.info(f"Requesting llm response with approx {approximate_tokens} tokens")
        result = self.adapter.complete(model=self.model, messages=messages, object_model=object_model,
                                       temperature=temperature, num_ctx=num_ctx, num_predict=num_predict)
        return result.object
