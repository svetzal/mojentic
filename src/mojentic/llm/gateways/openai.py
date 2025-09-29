import json
from itertools import islice
from typing import Type, List, Iterable, Optional

import numpy as np
import structlog
from openai import OpenAI, BadRequestError
from pydantic import BaseModel

from mojentic.llm.gateways.llm_gateway import LLMGateway
from mojentic.llm.gateways.models import LLMToolCall, LLMGatewayResponse, LLMMessage
from mojentic.llm.gateways.openai_messages_adapter import adapt_messages_to_openai
from mojentic.llm.gateways.openai_model_registry import get_model_registry, ModelType
from mojentic.llm.gateways.tokenizer_gateway import TokenizerGateway
from mojentic.llm.tools.llm_tool import LLMTool

logger = structlog.get_logger()


class OpenAIGateway(LLMGateway):
    """
    This class is a gateway to the OpenAI LLM service.

    Parameters
    ----------
    api_key : str
        The OpenAI API key to use.
    """

    def __init__(self, api_key: str, base_url: Optional[str] = None):
        self.client = OpenAI(api_key=api_key, base_url=base_url)
        self.model_registry = get_model_registry()

    def _is_reasoning_model(self, model: str) -> bool:
        """
        Determine if a model is a reasoning model that requires max_completion_tokens.

        Parameters
        ----------
        model : str
            The model name to classify.

        Returns
        -------
        bool
            True if the model is a reasoning model, False if it's a chat model.
        """
        return self.model_registry.is_reasoning_model(model)

    def _adapt_parameters_for_model(self, model: str, args: dict) -> dict:
        """
        Adapt parameters based on the model type and capabilities.

        Parameters
        ----------
        model : str
            The model name.
        args : dict
            The original arguments.

        Returns
        -------
        dict
            The adapted arguments with correct parameter names for the model type.
        """
        adapted_args = args.copy()
        capabilities = self.model_registry.get_model_capabilities(model)

        logger.debug("Adapting parameters for model",
                    model=model,
                    model_type=capabilities.model_type.value,
                    supports_tools=capabilities.supports_tools,
                    supports_streaming=capabilities.supports_streaming)

        # Handle token limit parameter conversion
        if 'max_tokens' in adapted_args:
            token_param = capabilities.get_token_limit_param()
            if token_param != 'max_tokens':
                # Convert max_tokens to max_completion_tokens for reasoning models
                adapted_args[token_param] = adapted_args.pop('max_tokens')
                logger.info("Converted token limit parameter for model",
                           model=model,
                           from_param='max_tokens',
                           to_param=token_param,
                           value=adapted_args[token_param])

        # Validate tool usage for models that don't support tools
        if 'tools' in adapted_args and adapted_args['tools'] and not capabilities.supports_tools:
            logger.warning("Model does not support tools, removing tool configuration",
                          model=model,
                          num_tools=len(adapted_args['tools']))
            adapted_args['tools'] = None  # Set to None instead of removing the key

        return adapted_args

    def _validate_model_parameters(self, model: str, args: dict) -> None:
        """
        Validate that the parameters are compatible with the model.

        Parameters
        ----------
        model : str
            The model name.
        args : dict
            The arguments to validate.
        """
        capabilities = self.model_registry.get_model_capabilities(model)

        # Warning for tools on reasoning models that don't support them
        if (capabilities.model_type == ModelType.REASONING and
            not capabilities.supports_tools and
            'tools' in args and args['tools']):
            logger.warning(
                "Reasoning model may not support tools",
                model=model,
                num_tools=len(args['tools'])
            )

        # Validate token limits (check both possible parameter names)
        token_value = args.get('max_tokens') or args.get('max_completion_tokens')
        if token_value and capabilities.max_output_tokens:
            if token_value > capabilities.max_output_tokens:
                logger.warning(
                    "Requested token limit exceeds model maximum",
                    model=model,
                    requested=token_value,
                    max_allowed=capabilities.max_output_tokens
                )

    def complete(self, **kwargs) -> LLMGatewayResponse:
        """
        Complete the LLM request by delegating to the OpenAI service.

        Keyword Arguments
        ----------------
        model : str
            The name of the model to use.
        messages : List[LLMMessage]
            A list of messages to send to the LLM.
        object_model : Optional[Type[BaseModel]]
            The model to use for validating the response.
        tools : Optional[List[LLMTool]]
            A list of tools to use with the LLM. If a tool call is requested, the tool will be called and the output
            will be included in the response.
        temperature : float, optional
            The temperature to use for the response. Defaults to 1.0.
        num_ctx : int, optional
            The number of context tokens to use. Defaults to 32768.
        max_tokens : int, optional
            The maximum number of tokens to generate. Defaults to 16384.
        num_predict : int, optional
            The number of tokens to predict. Defaults to no limit.

        Returns
        -------
        LLMGatewayResponse
            The response from the OpenAI service.
        """
        # Extract parameters from kwargs with defaults
        model = kwargs.get('model')
        messages = kwargs.get('messages')
        object_model = kwargs.get('object_model', None)
        tools = kwargs.get('tools', None)
        temperature = kwargs.get('temperature', 1.0)
        num_ctx = kwargs.get('num_ctx', 32768)
        max_tokens = kwargs.get('max_tokens', 16384)
        num_predict = kwargs.get('num_predict', -1)

        if not model:
            raise ValueError("'model' parameter is required")
        if not messages:
            raise ValueError("'messages' parameter is required")

        # Convert parameters to dict for processing
        args = {
            'model': model,
            'messages': messages,
            'object_model': object_model,
            'tools': tools,
            'temperature': temperature,
            'num_ctx': num_ctx,
            'max_tokens': max_tokens,
            'num_predict': num_predict
        }

        # Adapt parameters based on model type
        try:
            adapted_args = self._adapt_parameters_for_model(model, args)
        except Exception as e:
            logger.error("Failed to adapt parameters for model",
                        model=model,
                        error=str(e))
            raise

        # Validate parameters after adaptation
        self._validate_model_parameters(model, adapted_args)

        openai_args = {
            'model': adapted_args['model'],
            'messages': adapt_messages_to_openai(adapted_args['messages']),
        }

        # Add temperature if specified
        if 'temperature' in adapted_args:
            openai_args['temperature'] = adapted_args['temperature']

        completion = self.client.chat.completions.create

        if adapted_args['object_model'] is not None:
            completion = self.client.beta.chat.completions.parse
            openai_args['response_format'] = adapted_args['object_model']

        if adapted_args.get('tools') is not None:
            openai_args['tools'] = [t.descriptor for t in adapted_args['tools']]

        # Handle both max_tokens (for chat models) and max_completion_tokens (for reasoning models)
        if 'max_tokens' in adapted_args:
            openai_args['max_tokens'] = adapted_args['max_tokens']
        elif 'max_completion_tokens' in adapted_args:
            openai_args['max_completion_tokens'] = adapted_args['max_completion_tokens']

        logger.debug("Making OpenAI API call",
                    model=openai_args['model'],
                    has_tools='tools' in openai_args,
                    has_object_model='response_format' in openai_args,
                    token_param='max_completion_tokens' if 'max_completion_tokens' in openai_args else 'max_tokens')

        try:
            response = completion(**openai_args)
        except BadRequestError as e:
            # Enhanced error handling for parameter issues
            if "max_tokens" in str(e) and "max_completion_tokens" in str(e):
                logger.error("Parameter error detected - model may require different token parameter",
                            model=model,
                            error=str(e),
                            suggestion="This model may be a reasoning model requiring max_completion_tokens")
            raise e
        except Exception as e:
            logger.error("OpenAI API call failed",
                        model=model,
                        error=str(e))
            raise e

        object = None
        tool_calls: List[LLMToolCall] = []

        if adapted_args.get('object_model') is not None:
            try:
                response_content = response.choices[0].message.content
                if response_content is not None:
                    object = adapted_args['object_model'].model_validate_json(response_content)
                else:
                    logger.error("No response content available for object validation", object_model=adapted_args['object_model'])
            except Exception as e:
                response_content = response.choices[0].message.content if response.choices else "No response content"
                logger.error("Failed to validate model", error=str(e), response=response_content,
                           object_model=adapted_args['object_model'])

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
