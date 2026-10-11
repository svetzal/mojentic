import asyncio
import json
import os
from collections.abc import AsyncIterator, Iterator
from contextlib import closing
from typing import TYPE_CHECKING, Optional
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
from mojentic.llm.gateways.stream_events import (
    StreamError,
    StreamErrorReason,
    StreamEvent,
)
from mojentic.llm.recovery import (
    Capabilities,
    RecoveryCall,
    RecoveryPolicy,
    preparation_error,
)
from mojentic.llm.recovery_stream import (
    RecoveryStreamEvent,
    recover_stream,
    synchronous_stream,
)
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

    def __init__(
        self, settings: OMLXSettings, http_transport: httpx.BaseTransport | None = None
    ):
        self._client = httpx.Client(
            base_url=settings.base_url,
            headers=settings.headers,
            timeout=settings.timeout,
            transport=http_transport,
        )

    def get(self, path: str) -> httpx.Response:
        """Send ``GET path`` and return the response."""
        return self._checked(self._client.get(path))

    def post(self, path: str, body: dict | None = None) -> httpx.Response:
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
        Transport for legacy completions, embeddings and model management. Opt-in
        completion recovery uses a dedicated owned HTTP transport.
    recovery_policy : RecoveryPolicy, optional
        Opt in to ordinary, structured and streaming request recovery. Recovery
        disables the active response read timeout; other timeout settings remain.
    recovery_call : RecoveryCall, optional
        Cancellation for a synchronous operation. Use a fresh call per operation.

    Notes
    -----
    Legacy non-2xx responses raise ``httpx.HTTPStatusError``. Recovery-enabled
    completion paths raise typed ``RecoveryError`` with private cause inspection.
    Raw ``complete_stream_events`` remains single-request and reports provider errors.
    """

    def __init__(
        self,
        host: str | None = None,
        api_key: str | None = None,
        timeout: float | None = None,
        transport: OMLXTransport | None = None,
        recovery_policy: RecoveryPolicy | None = None,
        recovery_call: RecoveryCall | None = None,
    ) -> None:
        self.settings = omlx_settings(
            host=host, api_key=api_key, timeout=timeout, environ=os.environ
        )
        self.transport = transport or OMLXTransport(self.settings)
        self.recovery_policy = recovery_policy
        self.recovery_call = recovery_call

    def complete(
        self,
        model: str,
        messages: list[LLMMessage],
        object_model: type[BaseModel] | None = None,
        tools: list[LLMTool] | None = None,
        config: Optional["CompletionConfig"] = None,
        temperature: float = 1.0,
        num_ctx: int = 32768,
        max_tokens: int = 16384,
        num_predict: int = -1,
    ) -> LLMGatewayResponse:
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
        if self.recovery_policy is not None:
            return asyncio.run(
                self.complete_with_recovery(
                    model=model,
                    messages=messages,
                    config=config,
                    tools=tools,
                    object_model=object_model,
                    temperature=temperature,
                    num_ctx=num_ctx,
                    max_tokens=max_tokens,
                    num_predict=num_predict,
                )
            )
        config = config or _config_from_arguments(
            temperature, num_ctx, max_tokens, num_predict
        )
        body = omlx_chat_body(
            model, messages, config, tools=tools, object_model=object_model
        )
        response = self.transport.post("/chat/completions", body)
        result = omlx_gateway_response(
            response.json(), self._response_format_warning(model, body, response)
        )
        if object_model is not None:
            result.object = _validated_object(object_model, result.content)
        return result

    def recovery_capabilities(self) -> Capabilities:
        """Report supported request recovery and unsupported remote facilities."""
        return Capabilities(streaming_recovery=True)

    def _recovery_body(self, args: dict, streaming: bool) -> bytes:
        config = args.get("config") or _config_from_arguments(
            args.get("temperature", 1.0),
            args.get("num_ctx", 32768),
            args.get("max_tokens", 16384),
            args.get("num_predict", -1),
        )
        body = omlx_chat_body(
            args["model"],
            args["messages"],
            config,
            tools=args.get("tools"),
            object_model=args.get("object_model"),
        )
        if streaming:
            if args.get("object_model") is not None:
                raise ValueError("structured streaming is unsupported")
            body |= {"stream": True, "stream_options": {"include_usage": True}}
        return json.dumps(
            body, ensure_ascii=False, separators=(",", ":"), allow_nan=False
        ).encode("utf-8")

    def _recovery_headers(self) -> dict[str, str]:
        return self.settings.headers | {
            "Content-Type": "application/json",
            "Accept-Encoding": "identity",
        }

    async def complete_with_recovery(
        self, call: RecoveryCall | None = None, **args
    ) -> LLMGatewayResponse:
        """Recover one ordinary or structured completion, retaining typed failure evidence.

        Recovery bypasses the legacy transport and disables active read timeouts.

        Parameters
        ----------
        call : RecoveryCall, optional
            Cancellation for this operation, overriding the gateway call.
        **args
            The model, messages, tools, schema and controls accepted by ``complete``.

        Returns
        -------
        LLMGatewayResponse
            Provider response with a typed recovery report.

        Raises
        ------
        RecoveryError
            Recovery refused, interrupted, cancelled or received an invalid response.
        ValueError
            No recovery policy is configured.
        """
        from mojentic.llm.gateways.omlx_recovery import OMLXRecovery, decode_completion

        if self.recovery_policy is None:
            raise ValueError("configure recovery_policy before using recovery")
        operation = "structured" if args.get("object_model") is not None else "ordinary"
        try:
            body = self._recovery_body(args, False)
        except (ValueError, TypeError, KeyError, OSError) as cause:
            raise preparation_error(cause, operation, "omlx") from None
        engine = OMLXRecovery(
            self.recovery_policy,
            call or self.recovery_call or RecoveryCall(),
            operation,
        )
        result, report = await engine.run(
            self.settings.base_url + "/chat/completions",
            body,
            self._recovery_headers(),
            httpx.Timeout(self.settings.timeout, read=None),
            lambda frame: decode_completion(frame, args.get("object_model")),
        )
        result.recovery_report = report
        result.metadata |= {"recovery": report.model_dump(mode="json")}
        return result

    async def complete_stream_with_recovery(
        self, call: RecoveryCall | None = None, **args
    ) -> AsyncIterator[RecoveryStreamEvent]:
        """Yield progress and exactly one completed or failed recovery outcome.

        Closing the iterator cancels owned local HTTP; remote termination is unknown.
        Raw complete_stream_events remains a single-request compatibility API.

        Parameters
        ----------
        call : RecoveryCall, optional
            Cancellation for this operation, overriding the gateway call.
        **args
            The model, messages, tools and controls accepted by ``complete_stream``.

        Yields
        ------
        RecoveryStreamEvent
            Provider progress followed by one completed or failed terminal outcome.

        Raises
        ------
        ValueError
            No recovery policy is configured.
        """
        from mojentic.llm.gateways.omlx_recovery import (
            OMLXStreamRecovery,
            decode_completion,
        )

        if self.recovery_policy is None:
            raise ValueError("configure recovery_policy before using recovery")
        try:
            body = self._recovery_body(args, True)
        except (ValueError, TypeError, KeyError, OSError) as cause:
            error = preparation_error(cause, "streaming", "omlx")
            yield RecoveryStreamEvent(
                kind="failed",
                identity=error.report.identity,
                progress=error.report.progress,
                report=error.report,
                error=error,
                outcome="ineligible",
            )
            return
        events = recover_stream(
            self.settings.base_url + "/chat/completions",
            body,
            self._recovery_headers(),
            httpx.Timeout(self.settings.timeout, read=None),
            decode_completion,
            self.recovery_policy,
            call or self.recovery_call or RecoveryCall(),
            _engine_type=OMLXStreamRecovery,
        )
        try:
            async for event in events:
                yield event
        finally:
            await events.aclose()

    @staticmethod
    def _response_format_warning(
        model: str, body: dict, response: httpx.Response
    ) -> str | None:
        warnings = response.headers.get_list("warning")
        if not warnings or not requests_structured_output(body):
            return None
        warning = ", ".join(warnings)
        logger.warning(
            "oMLX did not enforce the requested response format",
            model=model,
            response_format_warning=warning,
        )
        return warning

    def complete_stream(
        self,
        model: str,
        messages: list[LLMMessage],
        object_model: type[BaseModel] | None = None,
        tools: list[LLMTool] | None = None,
        config: Optional["CompletionConfig"] = None,
        temperature: float = 1.0,
        num_ctx: int = 32768,
        max_tokens: int = 16384,
        num_predict: int = -1,
    ) -> Iterator[StreamingResponse]:
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
            raise NotImplementedError(
                "Streaming with structured output (object_model) is not supported"
            )
        if self.recovery_policy is not None:
            events = synchronous_stream(
                self.complete_stream_with_recovery(
                    model=model,
                    messages=messages,
                    config=config,
                    tools=tools,
                    temperature=temperature,
                    num_ctx=num_ctx,
                    max_tokens=max_tokens,
                    num_predict=num_predict,
                )
            )
            with closing(events):
                for event in events:
                    if event.kind == "failed":
                        raise event.error
                    if event.kind == "content":
                        yield StreamingResponse(content=event.text)
                    elif event.kind == "reasoning":
                        yield StreamingResponse(thinking=event.text)
                    elif event.kind == "completed" and event.response.tool_calls:
                        yield StreamingResponse(tool_calls=event.response.tool_calls)
            return
        config = config or _config_from_arguments(
            temperature, num_ctx, max_tokens, num_predict
        )
        body = omlx_chat_body(model, messages, config, tools=tools) | {"stream": True}
        lines = self.transport.stream_lines("/chat/completions", body)
        with closing(lines):
            yield from omlx_stream_chunks(drop_keepalive_frames(lines))

    def complete_stream_events(
        self, model: str, messages: list[LLMMessage], config: "CompletionConfig"
    ) -> Iterator[StreamEvent]:
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
        body = omlx_chat_body(model, messages, config) | {
            "stream": True,
            "stream_options": {"include_usage": True},
        }
        lines = self.transport.stream_lines("/chat/completions", body)
        try:
            with closing(lines):
                yield from parse_openai_stream(drop_keepalive_frames(lines))
        except httpx.HTTPStatusError as e:
            yield StreamError(
                reason=StreamErrorReason.PROVIDER_ERROR,
                detail=omlx_error_detail(e.response),
            )
        except httpx.HTTPError as e:
            yield StreamError(reason=StreamErrorReason.REQUEST_FAILED, detail=str(e))

    def get_available_models(self) -> list[str]:
        """
        Get the ids of the models the server offers, sorted alphabetically.

        Returns
        -------
        List[str]
            The model ids.
        """
        return sorted(
            model["id"] for model in self.transport.get("/models").json()["data"]
        )

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

    def calculate_embeddings(self, text: str, model: str | None = None) -> list[float]:
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


def _config_from_arguments(
    temperature: float, num_ctx: int, max_tokens: int, num_predict: int
) -> "CompletionConfig":
    from mojentic.llm.completion_config import CompletionConfig

    return CompletionConfig(
        temperature=temperature,
        num_ctx=num_ctx,
        max_tokens=max_tokens,
        num_predict=num_predict,
    )


def _validated_object(
    object_model: type[BaseModel], content: str | None
) -> BaseModel | None:
    if content is None:
        logger.error(
            "No response content available for object validation",
            object_model=object_model,
        )
        return None
    try:
        return object_model.model_validate_json(content)
    except ValueError as e:
        logger.error(
            "Failed to validate model",
            error=str(e),
            response=content,
            object_model=object_model,
        )
        return None


def _path_segment(model: str) -> str:
    if not model.strip():
        raise ValueError("oMLX model id must not be blank")
    return quote(model, safe="")
