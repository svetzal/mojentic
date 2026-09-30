import os
from contextlib import closing
from typing import Iterator, List, Optional, Type, TYPE_CHECKING
from urllib.parse import quote

import httpx
import structlog
from pydantic import BaseModel

from mojentic.llm.gateways.llm_gateway import LLMGateway
from mojentic.llm.gateways.models import LLMGatewayResponse, LLMMessage
from mojentic.llm.gateways.ollama import StreamingResponse
from mojentic.llm.gateways.omlx_protocol import (
    OMLXSettings,
    omlx_chat_body,
    omlx_error_detail,
    omlx_gateway_response,
    omlx_settings,
    requests_structured_output,
)
from mojentic.llm.gateways.omlx_stream import drop_keepalive_frames, omlx_stream_chunks
from mojentic.llm.gateways.openai_stream_events import parse_openai_stream
from mojentic.llm.gateways.stream_events import StreamError, StreamErrorReason, StreamEvent
from mojentic.llm.tools.llm_tool import LLMTool

if TYPE_CHECKING:
    from mojentic.llm.completion_config import CompletionConfig

logger = structlog.get_logger()


class OMLXTransport:
    """
    Sends HTTP requests to an oMLX server's ``/v1`` API.

    A thin wrapper around an ``httpx.Client``. Paths are relative to the settings'
    ``base_url``. A non-2xx response raises ``httpx.HTTPStatusError`` after its body has been
    read, so the error carries the status and the body. Nothing is retried.

    Parameters
    ----------
    settings : OMLXSettings
        Base URL, headers and timeout.
    http_transport : httpx.BaseTransport, optional
        The underlying httpx transport. Defaults to httpx's network transport.
    """

    def __init__(self, settings: OMLXSettings, http_transport: Optional[httpx.BaseTransport] = None):
        self._client = httpx.Client(base_url=settings.base_url, headers=settings.headers,
                                    timeout=settings.timeout, transport=http_transport)

    def get(self, path: str) -> httpx.Response:
        """Send ``GET path`` and return the response."""
        return self._checked(self._client.get(path))

    def post(self, path: str, body: Optional[dict] = None) -> httpx.Response:
        """Send ``POST path`` with an optional JSON body and return the response."""
        return self._checked(self._client.post(path, json=body))

    def stream_lines(self, path: str, body: dict) -> Iterator[str]:
        """Send ``POST path`` as one streaming request and yield each response line."""
        with self._client.stream("POST", path, json=body) as response:
            if response.is_error:
                response.read()
            response.raise_for_status()
            yield from response.iter_lines()

    @staticmethod
    def _checked(response: httpx.Response) -> httpx.Response:
        response.raise_for_status()
        return response


class OMLXGateway(LLMGateway):
    """
    A gateway to an `oMLX <https://github.com/jundot/omlx>`_ server, an LLM server for Apple Silicon.

    oMLX speaks the OpenAI chat completions protocol. This gateway sends requests with no
    per-model adaptation, maps ``reasoning_content`` to ``thinking``, and keeps usage exactly
    as the server reports it.

    Parameters
    ----------
    host : str, optional
        The server host, without ``/v1``. Defaults to ``OMLX_HOST``, then
        ``http://localhost:8000``. The gateway adds ``/v1`` to every path.
    api_key : str, optional
        Sent as ``Authorization: Bearer <key>``. Defaults to ``OMLX_API_KEY``. Without a key,
        no authorization header is sent.
    timeout : float, optional
        The timeout in seconds for every request, including model load. Defaults to
        ``OMLX_TIMEOUT`` (in milliseconds), then 600 seconds.
    transport : OMLXTransport, optional
        The transport every request goes through. Defaults to one over the resolved settings.

    Notes
    -----
    Non-2xx responses raise ``httpx.HTTPStatusError``; ``error.response`` carries the status
    and the oMLX error body. ``complete_stream_events`` reports them as ``PROVIDER_ERROR``.
    """

    def __init__(self, host: Optional[str] = None, api_key: Optional[str] = None, timeout: Optional[float] = None,
                 transport: Optional[OMLXTransport] = None):
        self.settings = omlx_settings(host=host, api_key=api_key, timeout=timeout, environ=os.environ)
        self.transport = transport or OMLXTransport(self.settings)

    def complete(self, model: str, messages: List[LLMMessage], object_model: Optional[Type[BaseModel]] = None,
                 tools: Optional[List[LLMTool]] = None, config: Optional['CompletionConfig'] = None,
                 temperature: float = 1.0, num_ctx: int = 32768, max_tokens: int = 16384,
                 num_predict: int = -1) -> LLMGatewayResponse:
        """
        Complete one chat turn.

        When a structured output request comes back with a ``Warning`` header, oMLX did not
        enforce the format. The header value goes in ``metadata["response_format_warning"]``
        and a warning is logged. The content is still returned and, with ``object_model``,
        still validated.

        Parameters
        ----------
        model : str
            The model id, as ``get_available_models`` reports it.
        messages : List[LLMMessage]
            The conversation.
        object_model : Optional[Type[BaseModel]]
            Request JSON schema output with this model's schema and validate the content against it.
        tools : Optional[List[LLMTool]]
            Tools to offer. Requested calls come back in ``tool_calls``.
        config : Optional[CompletionConfig]
            Temperature, token limit, reasoning effort and response format. When None, one is
            built from ``temperature`` and ``max_tokens``.
        temperature, num_ctx, max_tokens, num_predict
            Deprecated: use ``config``. ``num_ctx`` and ``num_predict`` are never sent.

        Returns
        -------
        LLMGatewayResponse
            Content, thinking, tool calls, usage, provider model, finish reason and metadata.
            ``content`` is not an answer unless ``finish_reason`` is ``stop``.
        """
        config = config or _config_from_arguments(temperature, num_ctx, max_tokens, num_predict)
        body = omlx_chat_body(model, messages, config, tools=tools, object_model=object_model)
        response = self.transport.post("/chat/completions", body)
        result = omlx_gateway_response(response.json(), self._response_format_warning(model, body, response))
        if object_model is not None:
            result.object = _validated_object(object_model, result.content)
        return result

    @staticmethod
    def _response_format_warning(model: str, body: dict, response: httpx.Response) -> Optional[str]:
        warnings = response.headers.get_list("warning")
        if not warnings or not requests_structured_output(body):
            return None
        warning = ", ".join(warnings)
        logger.warning("oMLX did not enforce the requested response format", model=model,
                       response_format_warning=warning)
        return warning

    def complete_stream(self, model: str, messages: List[LLMMessage],
                        object_model: Optional[Type[BaseModel]] = None, tools: Optional[List[LLMTool]] = None,
                        config: Optional['CompletionConfig'] = None, temperature: float = 1.0,
                        num_ctx: int = 32768, max_tokens: int = 16384,
                        num_predict: int = -1) -> Iterator[StreamingResponse]:
        """
        Stream one chat turn as legacy chunks.

        Content arrives as content chunks and ``reasoning_content`` as thinking chunks. Tool
        calls are yielded together, complete, when the turn finishes with ``tool_calls``.
        Keep-alive frames are dropped. Closing the generator closes the request.

        Parameters are as for :meth:`complete`, except that ``object_model`` is not supported.

        Raises
        ------
        NotImplementedError
            When ``object_model`` is given.
        """
        if object_model is not None:
            raise NotImplementedError("Streaming with structured output (object_model) is not supported")
        config = config or _config_from_arguments(temperature, num_ctx, max_tokens, num_predict)
        body = omlx_chat_body(model, messages, config, tools=tools) | {"stream": True}
        lines = self.transport.stream_lines("/chat/completions", body)
        with closing(lines):
            yield from omlx_stream_chunks(drop_keepalive_frames(lines))

    def complete_stream_events(self, model: str, messages: List[LLMMessage],
                               config: 'CompletionConfig') -> Iterator[StreamEvent]:
        """
        Stream one turn as events, with terminal completion evidence.

        Sends one streaming request with no tools, no retries and
        ``stream_options: {"include_usage": true}``. Keep-alive frames are dropped before
        parsing, so they never become evidence. ``reasoning_content`` produces no events. The
        turn completes only when oMLX reports ``finish_reason: "stop"`` and then sends
        ``data: [DONE]``. Closing the generator closes the HTTP request.

        Parameters
        ----------
        model : str
            The model id.
        messages : List[LLMMessage]
            The messages to send.
        config : CompletionConfig
            Configuration for the request.

        Yields
        ------
        StreamEvent
            Content events followed by exactly one terminal event.
        """
        body = omlx_chat_body(model, messages, config) | {"stream": True, "stream_options": {"include_usage": True}}
        lines = self.transport.stream_lines("/chat/completions", body)
        try:
            with closing(lines):
                yield from parse_openai_stream(drop_keepalive_frames(lines))
        except httpx.HTTPStatusError as e:
            yield StreamError(reason=StreamErrorReason.PROVIDER_ERROR, detail=omlx_error_detail(e.response))
        except httpx.HTTPError as e:
            yield StreamError(reason=StreamErrorReason.REQUEST_FAILED, detail=str(e))

    def get_available_models(self) -> List[str]:
        """
        Get the ids of the models the server offers, sorted alphabetically.

        Returns
        -------
        List[str]
            The model ids.
        """
        return sorted(model["id"] for model in self.transport.get("/models").json()["data"])

    def load_model(self, model: str) -> None:
        """
        Load a model into memory and wait until it is there.

        A chat request loads its model automatically; use this to warm a model up ahead of
        time. The gateway timeout covers the wait.

        Parameters
        ----------
        model : str
            The model id.
        """
        self.transport.post(f"/models/{_path_segment(model)}/load")

    def unload_model(self, model: str) -> None:
        """
        Unload a model from memory.

        Parameters
        ----------
        model : str
            The model id.

        Raises
        ------
        httpx.HTTPStatusError
            A 400 ``invalid_request_error`` when the model is not loaded.
        """
        self.transport.post(f"/models/{_path_segment(model)}/unload")

    def calculate_embeddings(self, text: str, model: Optional[str] = None) -> List[float]:
        """
        Calculate embeddings for the text in one request, with no client-side chunking.

        Parameters
        ----------
        text : str
            The text to embed.
        model : str
            The embedding model id. Required: oMLX has no standard embedding model.

        Returns
        -------
        List[float]
            The embedding.

        Raises
        ------
        ValueError
            When ``model`` is missing or empty. No request is sent.
        httpx.HTTPStatusError
            A 400 ``invalid_request_error`` when the model is not an embedding model.
        """
        if not model or not model.strip():
            raise ValueError("oMLX has no default embedding model; pass 'model'")
        response = self.transport.post("/embeddings", {"model": model, "input": text})
        return response.json()["data"][0]["embedding"]


def _config_from_arguments(temperature: float, num_ctx: int, max_tokens: int, num_predict: int) -> 'CompletionConfig':
    from mojentic.llm.completion_config import CompletionConfig
    return CompletionConfig(temperature=temperature, num_ctx=num_ctx, max_tokens=max_tokens, num_predict=num_predict)


def _validated_object(object_model: Type[BaseModel], content: Optional[str]) -> Optional[BaseModel]:
    if content is None:
        logger.error("No response content available for object validation", object_model=object_model)
        return None
    try:
        return object_model.model_validate_json(content)
    except ValueError as e:
        logger.error("Failed to validate model", error=str(e), response=content, object_model=object_model)
        return None


def _path_segment(model: str) -> str:
    if not model.strip():
        raise ValueError("oMLX model id must not be blank")
    return quote(model, safe="")
