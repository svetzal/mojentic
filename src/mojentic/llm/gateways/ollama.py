import json
from contextlib import closing
from typing import List, Iterator, Optional, TYPE_CHECKING, Union

import httpx
import structlog
from ollama import Client, Options, ChatResponse, ResponseError
from pydantic import BaseModel, ValidationError

from mojentic.llm.gateways.llm_gateway import LLMGateway
from mojentic.llm.gateways.models import LLMMessage, LLMToolCall, LLMGatewayResponse
from mojentic.llm.gateways.ollama_messages_adapter import adapt_messages_to_ollama
from mojentic.llm.gateways.ollama_stream_events import ollama_metadata, ollama_usage, parse_ollama_stream
from mojentic.llm.gateways.stream_events import StreamError, StreamErrorReason, StreamEvent

if TYPE_CHECKING:
    from mojentic.llm.completion_config import CompletionConfig, ResponseFormat

logger = structlog.get_logger()


def ollama_format(response_format: Optional['ResponseFormat']) -> Optional[Union[str, dict]]:
    """
    Translate a configured response format into the Ollama ``format`` request value.

    Parameters
    ----------
    response_format : Optional[ResponseFormat]
        The configured format, or None for the provider default.

    Returns
    -------
    Optional[Union[str, dict]]
        ``"json"``, a JSON schema, or None when the request must omit ``format``
        (plain text is Ollama's default).
    """
    if response_format is None or response_format.type == "text":
        return None
    return response_format.json_schema if response_format.json_schema is not None else "json"


class StreamingResponse(BaseModel):
    """
    Wrapper for streaming response chunks.

    Attributes
    ----------
    content : Optional[str]
        Text content chunk from the LLM response.
    tool_calls : Optional[List]
        Tool calls from the LLM response (raw ollama format).
    thinking : Optional[str]
        Thinking/reasoning trace from the LLM response.
    """
    content: Optional[str] = None
    tool_calls: Optional[List] = None
    thinking: Optional[str] = None


class OllamaStreamTransport:
    """
    Sends one streaming ``/api/chat`` request and yields its decoded frames.

    A thin wrapper around the Ollama client. Closing the generator closes the HTTP
    response, which cancels the request.
    """

    def __init__(self, client: Client):
        self._client = client

    def stream_frames(self, request: dict) -> Iterator[dict]:
        """Send ``request`` as one streaming chat request and yield each frame as a dict."""
        with closing(self._client.chat(**request, stream=True)) as parts:
            for part in parts:
                yield part.model_dump(exclude_none=True)


class OllamaGateway(LLMGateway):
    """
    This class is a gateway to the Ollama LLM service.

    Parameters
    ----------
    host : str, optional
        The Ollama host to connect to. Defaults to "http://localhost:11434".
    headers : dict, optional
        The headers to send with the request. Defaults to an empty dict.
    timeout : optional
        The request timeout passed to the Ollama client.
    stream_transport : OllamaStreamTransport, optional
        The transport ``complete_stream_events`` uses. Defaults to one over this gateway's client.
    """

    def __init__(self, host="http://localhost:11434", headers={}, timeout=None,
                 stream_transport: Optional[OllamaStreamTransport] = None):
        self.client = Client(host=host, headers=headers, timeout=timeout)
        self.stream_transport = stream_transport or OllamaStreamTransport(self.client)

    def _extract_options_from_args(self, args):
        # Extract config if present, otherwise use individual kwargs
        config = args.get('config', None)
        if config:
            options = Options(
                temperature=config.temperature,
                num_ctx=config.num_ctx,
            )
            if config.num_predict > 0:
                options.num_predict = config.num_predict
            if config.max_tokens:
                options.num_predict = config.max_tokens
        else:
            options = Options(
                temperature=args.get('temperature', 1.0),
                num_ctx=args.get('num_ctx', 32768),
            )
            if args.get('num_predict', 0) > 0:
                options.num_predict = args['num_predict']
            if 'max_tokens' in args:
                options.num_predict = args['max_tokens']
        return options

    def complete(self, **args) -> LLMGatewayResponse:
        """
        Complete the LLM request by delegating to the Ollama service.

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
        max_tokens : int, optional
            The maximum number of tokens to generate. Defaults to 16384.
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

        # Handle reasoning effort - if config has reasoning_effort set, enable thinking
        config = args.get('config', None)
        if config and config.reasoning_effort is not None:
            ollama_args['think'] = True
            logger.info("Enabling extended thinking for Ollama", reasoning_effort=config.reasoning_effort)

        if 'object_model' in args and args['object_model'] is not None:
            ollama_args['format'] = args['object_model'].model_json_schema()
        elif (response_format := ollama_format(config.response_format if config else None)) is not None:
            ollama_args['format'] = response_format

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

        # Extract thinking content if present
        thinking = getattr(response.message, 'thinking', None)

        frame = response.model_dump()
        return LLMGatewayResponse(
            content=response.message.content,
            object=object,
            tool_calls=tool_calls,
            thinking=thinking,
            usage=ollama_usage(frame),
            model=response.model,
            finish_reason=response.done_reason,
            metadata=ollama_metadata(frame) or {},
        )

    def complete_stream(self, **args) -> Iterator[StreamingResponse]:
        """
        Stream the LLM response from Ollama service.

        Keyword Arguments
        ----------------
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
        max_tokens : int, optional
            The maximum number of tokens to generate. Defaults to 16384.
        num_predict : int, optional
            The number of tokens to predict. Defaults to no limit.

        Returns
        -------
        Iterator[StreamingResponse]
            An iterator of StreamingResponse objects containing response chunks.
        """
        logger.info("Delegating to Ollama for streaming completion", **args)

        ollama_args = self._stream_request(args)
        ollama_args['stream'] = True

        # Enable tool support if tools are provided
        if 'tools' in args and args['tools'] is not None:
            ollama_args['tools'] = [t.descriptor for t in args['tools']]

        stream = self.client.chat(**ollama_args)

        for chunk in stream:
            if chunk.message:
                # Yield content chunks as they arrive
                if chunk.message.content:
                    yield StreamingResponse(content=chunk.message.content)

                # Yield thinking chunks when they arrive
                if hasattr(chunk.message, 'thinking') and chunk.message.thinking:
                    yield StreamingResponse(thinking=chunk.message.thinking)

                # Yield tool calls when they arrive
                if chunk.message.tool_calls:
                    yield StreamingResponse(tool_calls=chunk.message.tool_calls)

    def complete_stream_events(self, model: str, messages: List[LLMMessage],
                               config: 'CompletionConfig') -> Iterator[StreamEvent]:
        """
        Stream one turn as events, with terminal completion evidence.

        Sends one streaming request with no tools. The turn completes only when Ollama
        reports ``done: true`` with ``done_reason: "stop"``. Closing the generator closes
        the HTTP request.

        Parameters
        ----------
        model : str
            The name of the model to use, as appears in `ollama list`.
        messages : List[LLMMessage]
            The messages to send.
        config : CompletionConfig
            Configuration for the request.

        Yields
        ------
        StreamEvent
            Content events followed by exactly one terminal event.
        """
        frames = self.stream_transport.stream_frames(
            self._stream_request({'model': model, 'messages': messages, 'config': config}))
        try:
            with closing(frames):
                yield from parse_ollama_stream(frames)
        except ResponseError as e:
            yield StreamError(reason=StreamErrorReason.PROVIDER_ERROR,
                              detail={"status_code": e.status_code, "error": e.error})
        except (json.JSONDecodeError, ValidationError) as e:
            yield StreamError(reason=StreamErrorReason.INVALID_STREAM_EVENT, detail=str(e))
        except (ConnectionError, httpx.HTTPError) as e:
            yield StreamError(reason=StreamErrorReason.REQUEST_FAILED, detail=str(e))

    def _stream_request(self, args: dict) -> dict:
        """Build the chat request shared by both streaming APIs, without tools or the stream flag."""
        request = {
            'model': args['model'],
            'messages': adapt_messages_to_ollama(args['messages']),
            'options': self._extract_options_from_args(args),
        }

        # Handle reasoning effort - if config has reasoning_effort set, enable thinking
        config = args.get('config', None)
        if config and config.reasoning_effort is not None:
            request['think'] = True
            logger.info("Enabling extended thinking for Ollama streaming", reasoning_effort=config.reasoning_effort)

        response_format = ollama_format(config.response_format if config else None)
        if response_format is not None:
            request['format'] = response_format
        return request

    def get_available_models(self) -> List[str]:
        """
        Get the list of available local models, sorted alphabetically.

        Returns
        -------
        List[str]
            The list of available models, sorted alphabetically.
        """
        return sorted([m.model for m in self.client.list().models])

    def pull_model(self, model: str) -> None:
        """
        Pull the model from the Ollama service.

        Parameters
        ----------
        model : str
            The name of the model to pull.
        """
        self.client.pull(model)

    def calculate_embeddings(self, text: str, model: str = "mxbai-embed-large") -> List[float]:
        """
        Calculate embeddings for the given text using the specified model.

        Parameters
        ----------
        text : str
            The text to calculate embeddings for.
        model : str, optional
            The name of the model to use for embeddings. Defaults to "mxbai-embed-large".

        Returns
        -------
        list
            The embeddings for the text.
        """
        logger.debug("calculate_embeddings", text=text, model=model)
        embed = self.client.embeddings(model=model, prompt=text)
        return embed.embedding
