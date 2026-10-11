import asyncio
import json
from collections.abc import AsyncIterator, Iterator
from contextlib import closing
from typing import TYPE_CHECKING, Optional

import httpx
import structlog
from ollama import ChatResponse, Client, Image, Options, ResponseError
from pydantic import BaseModel, ValidationError

from mojentic.llm.gateways.llm_gateway import LLMGateway
from mojentic.llm.gateways.models import LLMGatewayResponse, LLMMessage, LLMToolCall
from mojentic.llm.gateways.ollama_messages_adapter import adapt_messages_to_ollama
from mojentic.llm.gateways.ollama_stream_events import (
    ollama_metadata,
    ollama_usage,
    parse_ollama_stream,
)
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
    recover,
)
from mojentic.llm.recovery_stream import (
    RecoveryStreamEvent,
    recover_stream,
    synchronous_stream,
)

if TYPE_CHECKING:
    from mojentic.llm.completion_config import CompletionConfig, ResponseFormat

logger = structlog.get_logger()


def ollama_format(response_format: Optional["ResponseFormat"]) -> str | dict | None:
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
    return (
        response_format.json_schema
        if response_format.json_schema is not None
        else "json"
    )


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

    content: str | None = None
    tool_calls: list | None = None
    thinking: str | None = None


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
    recovery_policy : RecoveryPolicy, optional
        Opt in to ordinary, structured, and tool-capable streaming request recovery.
    recovery_call : RecoveryCall, optional
        Cancellation for a synchronous broker/session operation. Use a fresh call per operation.
    stream_transport : OllamaStreamTransport, optional
        The transport ``complete_stream_events`` uses. Defaults to one over this gateway's client.
    """

    def __init__(
        self,
        host="http://localhost:11434",
        headers=None,
        timeout=None,
        stream_transport: OllamaStreamTransport | None = None,
        recovery_policy: RecoveryPolicy | None = None,
        recovery_call: RecoveryCall | None = None,
    ):
        if headers is None:
            headers = {}
        self.recovery_policy = recovery_policy
        self.recovery_call = recovery_call
        self._recovery_host = (
            host.rstrip("/") if isinstance(host, str) else "http://localhost:11434"
        )
        self._recovery_headers = dict(headers or {})
        self._recovery_timeout = timeout
        self.client = Client(host=host, headers=headers, timeout=timeout)
        self.stream_transport = stream_transport or OllamaStreamTransport(self.client)

    def _extract_options_from_args(self, args):
        # Extract config if present, otherwise use individual kwargs
        config = args.get("config", None)
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
                temperature=args.get("temperature", 1.0),
                num_ctx=args.get("num_ctx", 32768),
            )
            if args.get("num_predict", 0) > 0:
                options.num_predict = args["num_predict"]
            if "max_tokens" in args:
                options.num_predict = args["max_tokens"]
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
        if self.recovery_policy is not None:
            return asyncio.run(self.complete_with_recovery(**args))

        logger.info("Delegating to Ollama for completion", **args)

        ollama_args = self._completion_request(args)

        response: ChatResponse = self.client.chat(**ollama_args)

        structured_object = None

        if "object_model" in args:
            try:
                structured_object = args["object_model"].model_validate_json(
                    response.message.content
                )
            except ValidationError as e:
                logger.error(
                    "Failed to validate model in",
                    error=str(e),
                    response=response.message.content,
                    object_model=args["object_model"],
                )

        return self._completion_response(response, structured_object)

    def _completion_request(self, args: dict) -> dict:
        options = self._extract_options_from_args(args)

        ollama_args = {
            "model": args["model"],
            "messages": adapt_messages_to_ollama(args["messages"]),
            "options": options,
        }

        # Handle reasoning effort - if config has reasoning_effort set, enable thinking
        config = args.get("config", None)
        if config and config.reasoning_effort is not None:
            ollama_args["think"] = True
            if self.recovery_policy is None:
                logger.info(
                    "Enabling extended thinking for Ollama",
                    reasoning_effort=config.reasoning_effort,
                )

        if "object_model" in args and args["object_model"] is not None:
            ollama_args["format"] = args["object_model"].model_json_schema()
        elif (
            response_format := ollama_format(config.response_format if config else None)
        ) is not None:
            ollama_args["format"] = response_format

        if "tools" in args and args["tools"] is not None:
            ollama_args["tools"] = [t.descriptor for t in args["tools"]]

        return ollama_args

    def recovery_capabilities(self) -> Capabilities:
        """Report recovery support without implying remote cancellation or idempotency."""
        return Capabilities(streaming_recovery=True)

    async def complete_with_recovery(
        self, call: RecoveryCall | None = None, **args
    ) -> LLMGatewayResponse:
        """Complete one ordinary or structured request with safe recovery metadata.

        Raises
        ------
        RecoveryError
            Provider, protocol, capture, cancellation, or recovery admission failed.
        ValueError
            No recovery policy is configured.
        """
        if self.recovery_policy is None:
            raise ValueError(
                "configure recovery_policy before using complete_with_recovery"
            )
        operation = "structured" if args.get("object_model") is not None else "ordinary"
        try:
            request = self._completion_request(args)
            request["options"] = request["options"].model_dump(exclude_none=True)
            request["stream"] = False
            for message in request["messages"]:
                if message.get("images"):
                    message["images"] = [
                        Image(value=image).model_dump(mode="json")
                        for image in message["images"]
                    ]
            body = json.dumps(
                request, ensure_ascii=False, separators=(",", ":"), allow_nan=False
            ).encode("utf-8")
            headers = self._recovery_headers | {
                "Content-Type": "application/json",
                "Accept-Encoding": "identity",
            }
        except (ValueError, TypeError, KeyError, OSError) as cause:
            raise preparation_error(cause, operation) from None
        result, report = await recover(
            self._recovery_host + "/api/chat",
            body,
            headers,
            self._recovery_timeout,
            lambda frame: self._decode_recovery(frame, args.get("object_model")),
            self.recovery_policy,
            call or self.recovery_call or RecoveryCall(),
            operation,
        )
        result.recovery_report = report
        result.metadata = result.metadata | {"recovery": report.model_dump(mode="json")}
        return result

    def _decode_recovery(
        self, frame: object, object_model: type[BaseModel] | None
    ) -> LLMGatewayResponse:
        if not isinstance(frame, dict) or not isinstance(frame.get("message"), dict):
            raise TypeError("missing response message")
        if frame["message"].get("role") != "assistant":
            raise ValueError("invalid response role")
        if not isinstance(frame["message"].get("content", ""), str):
            raise TypeError("invalid response content")
        response = ChatResponse.model_validate(frame)
        object = (
            object_model.model_validate_json(response.message.content)
            if object_model is not None
            else None
        )
        return self._completion_response(response, object)

    def _completion_response(
        self, response: ChatResponse, object: BaseModel | None
    ) -> LLMGatewayResponse:
        tool_calls = []
        if response.message.tool_calls is not None:
            tool_calls = [
                LLMToolCall(
                    name=t.function.name,
                    arguments={
                        str(k): str(t.function.arguments[k])
                        for k in t.function.arguments
                    },
                )
                for t in response.message.tool_calls
            ]

        # Extract thinking content if present
        thinking = getattr(response.message, "thinking", None)

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
        if self.recovery_policy is not None:
            events = synchronous_stream(self.complete_stream_with_recovery(**args))
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

        logger.info("Delegating to Ollama for streaming completion", **args)

        ollama_args = self._stream_request(args)
        ollama_args["stream"] = True

        # Enable tool support if tools are provided
        if "tools" in args and args["tools"] is not None:
            ollama_args["tools"] = [t.descriptor for t in args["tools"]]

        stream = self.client.chat(**ollama_args)

        for chunk in stream:
            if chunk.message:
                # Yield content chunks as they arrive
                if chunk.message.content:
                    yield StreamingResponse(content=chunk.message.content)

                # Yield thinking chunks when they arrive
                if hasattr(chunk.message, "thinking") and chunk.message.thinking:
                    yield StreamingResponse(thinking=chunk.message.thinking)

                # Yield tool calls when they arrive
                if chunk.message.tool_calls:
                    yield StreamingResponse(tool_calls=chunk.message.tool_calls)

    async def complete_stream_with_recovery(
        self, call: RecoveryCall | None = None, **args
    ) -> AsyncIterator[RecoveryStreamEvent]:
        """Stream one tool-capable completion with explicit recovery terminal events.

        Consume ``completed`` or ``failed`` to determine the outcome. Closing this
        iterator closes locally owned HTTP; it does not prove remote termination.
        Raw ``complete_stream_events`` remains a single-turn compatibility API.
        """
        if self.recovery_policy is None:
            raise ValueError("configure recovery_policy before using recovery streams")
        try:
            request = self._stream_request(args)
            request["options"] = request["options"].model_dump(exclude_none=True)
            request["stream"] = True
            if args.get("tools") is not None:
                request["tools"] = [tool.descriptor for tool in args["tools"]]
            for message in request["messages"]:
                if message.get("images"):
                    message["images"] = [
                        Image(value=image).model_dump(mode="json")
                        for image in message["images"]
                    ]
            body = json.dumps(
                request, ensure_ascii=False, separators=(",", ":"), allow_nan=False
            ).encode("utf-8")
        except (ValueError, TypeError, KeyError, OSError) as cause:
            error = preparation_error(cause, "streaming")
            yield RecoveryStreamEvent(
                kind="failed",
                identity=error.report.identity,
                progress=error.report.progress,
                report=error.report,
                error=error,
                outcome="ineligible",
            )
            return
        headers = self._recovery_headers | {
            "Content-Type": "application/json",
            "Accept-Encoding": "identity",
        }
        events = recover_stream(
            self._recovery_host + "/api/chat",
            body,
            headers,
            self._recovery_timeout,
            self._decode_stream_recovery,
            self.recovery_policy,
            call or self.recovery_call or RecoveryCall(),
        )
        try:
            async for event in events:
                yield event
        finally:
            await events.aclose()

    def _decode_stream_recovery(self, frame: dict) -> LLMGatewayResponse:
        """Preserve native streaming tool arguments without ordinary-path conversion."""
        response = self._decode_recovery(frame, None)
        response.tool_calls = [
            LLMToolCall(
                id=call.get("id"),
                name=call["function"]["name"],
                arguments=call["function"]["arguments"],
            )
            for call in frame["message"].get("tool_calls", [])
        ]
        return response

    def complete_stream_events(
        self, model: str, messages: list[LLMMessage], config: "CompletionConfig"
    ) -> Iterator[StreamEvent]:
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
            self._stream_request(
                {"model": model, "messages": messages, "config": config}
            )
        )
        try:
            with closing(frames):
                yield from parse_ollama_stream(frames)
        except ResponseError as e:
            yield StreamError(
                reason=StreamErrorReason.PROVIDER_ERROR,
                detail={"status_code": e.status_code, "error": e.error},
            )
        except (json.JSONDecodeError, ValidationError) as e:
            yield StreamError(
                reason=StreamErrorReason.INVALID_STREAM_EVENT, detail=str(e)
            )
        except (ConnectionError, httpx.HTTPError) as e:
            yield StreamError(reason=StreamErrorReason.REQUEST_FAILED, detail=str(e))

    def _stream_request(self, args: dict) -> dict:
        """Build the chat request shared by both streaming APIs, without tools or the stream flag."""
        request = {
            "model": args["model"],
            "messages": adapt_messages_to_ollama(args["messages"]),
            "options": self._extract_options_from_args(args),
        }

        # Handle reasoning effort - if config has reasoning_effort set, enable thinking
        config = args.get("config", None)
        if config and config.reasoning_effort is not None:
            request["think"] = True
            logger.info(
                "Enabling extended thinking for Ollama streaming",
                reasoning_effort=config.reasoning_effort,
            )

        response_format = ollama_format(config.response_format if config else None)
        if response_format is not None:
            request["format"] = response_format
        return request

    def get_available_models(self) -> list[str]:
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

    def calculate_embeddings(
        self, text: str, model: str = "mxbai-embed-large"
    ) -> list[float]:
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
