import json
from itertools import islice
from typing import Type, List, Iterable

import numpy as np
import structlog
from openai import OpenAI

from mojentic.llm.gateways.llm_gateway import LLMGateway
from mojentic.llm.gateways.models import LLMToolCall, LLMGatewayResponse
from mojentic.llm.gateways.openai_messages_adapter import adapt_messages_to_openai
from mojentic.llm.gateways.tokenizer_gateway import TokenizerGateway

logger = structlog.get_logger()


class OpenAIGateway(LLMGateway):
    """
    This class is a gateway to the OpenAI LLM service.

    Parameters
    ----------
    api_key : str
        The OpenAI API key to use.
    """

    def __init__(self, api_key: str, base_url: str = None):
        self.client = OpenAI(api_key=api_key, base_url=base_url)

    def complete(self, **args) -> LLMGatewayResponse:
        """
        Complete the LLM request by delegating to the OpenAI service.

        Keyword Arguments
        ----------------
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
        tool_calls: List[LLMToolCall] = []

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
        """
        Get the list of available OpenAI models, sorted alphabetically.

        Returns
        -------
        list[str]
            The list of available models, sorted alphabetically.
        """
        return sorted([m.id for m in self.client.models.list()])

    def calculate_embeddings(self, text: str, model: str = "text-embedding-3-large") -> List[float]:
        """
        Calculate embeddings for the given text using the specified OpenAI model.

        Parameters
        ----------
        text : str
            The text to calculate embeddings for.
        model : str, optional
            The name of the OpenAI embeddings model to use. Defaults to "text-embedding-3-large".

        Returns
        -------
        list
            The embeddings for the text.
        """
        logger.debug("calculate_embeddings", text=text, model=model)

        embeddings = [self.client.embeddings.create(model=model, input=chunk).data[0].embedding
                      for chunk in self._chunked_tokens(text, 8191)]
        lengths = [len(embedding) for embedding in embeddings]

        average = np.average(embeddings, axis=0, weights=lengths)
        average = average / np.linalg.norm(average)
        average = average.tolist()

        return average

    def _batched(self, iterable: Iterable, n: int):
        """Batch data into tuples of length n. The last batch may be shorter."""
        # batched('ABCDEFG', 3) --> ABC DEF G
        if n < 1:
            raise ValueError('n must be at least one')
        it = iter(iterable)
        while batch := tuple(islice(it, n)):
            yield batch

    def _chunked_tokens(self, text, chunk_length):
        tokenizer = TokenizerGateway()
        tokens = tokenizer.encode(text)
        chunks_iterator = self._batched(tokens, chunk_length)
        yield from chunks_iterator
