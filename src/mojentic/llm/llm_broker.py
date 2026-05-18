import asyncio
import inspect
import json
import time
import warnings
from typing import List, Optional, Type, Iterator

import structlog
from pydantic import BaseModel

from mojentic.llm.completion_config import CompletionConfig
from mojentic.llm.gateways.llm_gateway import LLMGateway
from mojentic.llm.gateways.models import MessageRole, LLMMessage, LLMGatewayResponse, LLMToolCall
from mojentic.llm.gateways.ollama import OllamaGateway
from mojentic.llm.gateways.tokenizer_gateway import TokenizerGateway
from mojentic.llm.tools.runner import (
    SerialToolRunner,
    ToolRunner,
)
from mojentic.tracer.tracer_system import TracerSystem

logger = structlog.get_logger()


class MaxToolIterationsExceededError(Exception):
    """Raised when tool calls exceed the maximum allowed iterations."""


class LLMBroker():
    """
    This class is responsible for managing interaction with a Large Language Model. It abstracts
    the user
    from the specific mechanics of the LLM and provides a common interface for generating responses.
    """

    adapter: LLMGateway
    tokenizer: TokenizerGateway
    model: str
    tracer: Optional[TracerSystem]
    tool_runner: ToolRunner

    def __init__(self, model: str, gateway: Optional[LLMGateway] = None,
                 tokenizer: Optional[TokenizerGateway] = None,
                 tracer: Optional[TracerSystem] = None,
                 tool_runner: Optional[ToolRunner] = None):
        """
        Create an instance of the LLMBroker.

        Parameters
        ----------
        model
            The name of the model to use.
        gateway
            The gateway to use for communication with the LLM. If None, a gateway is created that
            will utilize a local
            Ollama server.
        tokenizer
            The gateway to use for tokenization. This is used to log approximate token counts for
            the LLM calls. If
            None, tiktoken's `cl100k_base` tokenizer is used.
        tracer
            Optional tracer system to record LLM calls and responses.
        tool_runner
            Strategy for executing tool calls returned by the LLM. Defaults to
            :class:`SerialToolRunner` for backward compatibility. Pass
            :class:`AsyncParallelToolRunner` (used by the realtime broker) or a
            custom :class:`ToolRunner` to change concurrency policy.
        """
        self.model = model

        # Use null_tracer if no tracer is provided
        from mojentic.tracer import null_tracer
        self.tracer = tracer or null_tracer

        if tokenizer is None:
            self.tokenizer = TokenizerGateway()
        else:
            self.tokenizer = tokenizer
        if gateway is None:
            self.adapter = OllamaGateway()
        else:
            self.adapter = gateway

        self.tool_runner = tool_runner or SerialToolRunner()

    def generate(self, messages: List[LLMMessage], tools=None,
                 config: Optional[CompletionConfig] = None,
                 temperature: Optional[float] = None, num_ctx: Optional[int] = None,
                 num_predict: Optional[int] = None, max_tokens: Optional[int] = None,
                 correlation_id: str = None) -> str:
        """
        Generate a text response from the LLM.

        Parameters
        ----------
        messages : LLMMessage
            A list of messages to send to the LLM.
        tools : List[Tool]
            A list of tools to use with the LLM. If a tool call is requested, the tool will be
            called and the output
            will be included in the response.
        config : Optional[CompletionConfig]
            Configuration object for LLM completion (recommended). If provided with individual
            kwargs, a DeprecationWarning is emitted.
        temperature : Optional[float]
            The temperature to use for the response. Deprecated: use config.
        num_ctx : Optional[int]
            The number of context tokens to use. Deprecated: use config.
        num_predict : Optional[int]
            The number of tokens to predict. Deprecated: use config.
        max_tokens : Optional[int]
            The maximum number of tokens to generate. Deprecated: use config.
        correlation_id : str
            UUID string that is copied from cause-to-affect for tracing events.

        Returns
        -------
        str
            The response from the LLM.

        Raises
        ------
        MaxToolIterationsExceededError
            If tool calls exceed config.max_tool_iterations.
        """
        # Handle config vs individual kwargs
        if config is not None and any(
                param is not None for param in [temperature, num_ctx, num_predict, max_tokens]):
            warnings.warn(
                "Both config and individual kwargs provided. Using config and ignoring kwargs. "
                "Individual kwargs are deprecated, use config=CompletionConfig(...) instead.",
                DeprecationWarning,
                stacklevel=2
            )
        elif config is None:
            # Build config from individual kwargs
            config = CompletionConfig(
                temperature=temperature if temperature is not None else 1.0,
                num_ctx=num_ctx if num_ctx is not None else 32768,
                num_predict=num_predict if num_predict is not None else -1,
                max_tokens=max_tokens if max_tokens is not None else 16384
            )

        if config.max_tool_iterations <= 0:
            raise MaxToolIterationsExceededError(
                f"Tool call iterations exceeded the maximum budget for model '{self.model}'. "
                f"Increase config.max_tool_iterations to allow more recursion."
            )
        approximate_tokens = len(self.tokenizer.encode(self._content_to_count(messages)))
        logger.info(f"Requesting llm response with approx {approximate_tokens} tokens")

        # Convert messages to serializable dict for audit
        messages_for_tracer = [m.model_dump() for m in messages]

        # Record LLM call in tracer
        tools_for_tracer = [{"name": t.name, "description": t.description} for t in
                            tools] if tools else None
        self.tracer.record_llm_call(
            self.model,
            messages_for_tracer,
            config.temperature,
            tools=tools_for_tracer,
            source=type(self),
            correlation_id=correlation_id
        )

        # Measure call duration for audit
        start_time = time.time()

        result: LLMGatewayResponse = self.adapter.complete(
            model=self.model,
            messages=messages,
            tools=tools,
            config=config,
            temperature=config.temperature,
            num_ctx=config.num_ctx,
            num_predict=config.num_predict,
            max_tokens=config.max_tokens)

        call_duration_ms = (time.time() - start_time) * 1000

        # Record LLM response in tracer
        tool_calls_for_tracer = [tc.model_dump() for tc in
                                 result.tool_calls] if result.tool_calls else None
        self.tracer.record_llm_response(
            self.model,
            result.content,
            tool_calls=tool_calls_for_tracer,
            call_duration_ms=call_duration_ms,
            source=type(self),
            correlation_id=correlation_id
        )

        if result.tool_calls and tools is not None:
            logger.info("Tool call requested")
            paired = self._dispatch_tool_batch(
                result.tool_calls,
                tools,
                caller="LLMBroker",
                correlation_id=correlation_id,
            )

            if paired:
                for tool_call, outcome in paired:
                    messages.append(
                        LLMMessage(role=MessageRole.Assistant, tool_calls=[tool_call])
                    )
                    messages.append(
                        LLMMessage(
                            role=MessageRole.Tool,
                            content=self._serialize_outcome(outcome),
                            tool_calls=[tool_call],
                        )
                    )
                return self.generate(
                    messages, tools,
                    config=config.model_copy(
                        update={"max_tool_iterations": config.max_tool_iterations - 1}
                    ),
                    correlation_id=correlation_id
                )

        return result.content

    def generate_stream(self, messages: List[LLMMessage], tools=None,
                        config: Optional[CompletionConfig] = None,
                        temperature: Optional[float] = None, num_ctx: Optional[int] = None,
                        num_predict: Optional[int] = None, max_tokens: Optional[int] = None,
                        correlation_id: str = None) -> Iterator[str]:
        """
        Generate a streaming text response from the LLM.

        This method mirrors generate() but yields content chunks as they arrive from the LLM,
        providing a better user experience for long-running requests. When tool calls are
        detected, tools are executed and the LLM is called recursively, with the new response
        also being streamed.

        Parameters
        ----------
        messages : List[LLMMessage]
            A list of messages to send to the LLM.
        tools : List[Tool]
            A list of tools to use with the LLM. If a tool call is requested, the tool will be
            called and the output will be included in the response.
        config : Optional[CompletionConfig]
            Configuration object for LLM completion (recommended). If provided with individual
            kwargs, a DeprecationWarning is emitted.
        temperature : Optional[float]
            The temperature to use for the response. Deprecated: use config.
        num_ctx : Optional[int]
            The number of context tokens to use. Deprecated: use config.
        num_predict : Optional[int]
            The number of tokens to predict. Deprecated: use config.
        max_tokens : Optional[int]
            The maximum number of tokens to generate. Deprecated: use config.
        correlation_id : str
            UUID string that is copied from cause-to-affect for tracing events.

        Yields
        ------
        str
            Content chunks as they arrive from the LLM.

        Raises
        ------
        MaxToolIterationsExceededError
            If tool calls exceed config.max_tool_iterations.
        """
        # Handle config vs individual kwargs
        if config is not None and any(
                param is not None for param in [temperature, num_ctx, num_predict, max_tokens]):
            warnings.warn(
                "Both config and individual kwargs provided. Using config and ignoring kwargs. "
                "Individual kwargs are deprecated, use config=CompletionConfig(...) instead.",
                DeprecationWarning,
                stacklevel=2
            )
        elif config is None:
            # Build config from individual kwargs
            config = CompletionConfig(
                temperature=temperature if temperature is not None else 1.0,
                num_ctx=num_ctx if num_ctx is not None else 32768,
                num_predict=num_predict if num_predict is not None else -1,
                max_tokens=max_tokens if max_tokens is not None else 16384
            )

        if config.max_tool_iterations <= 0:
            raise MaxToolIterationsExceededError(
                f"Tool call iterations exceeded the maximum budget for model '{self.model}'. "
                f"Increase config.max_tool_iterations to allow more recursion."
            )
        # Check if gateway supports streaming
        if not hasattr(self.adapter, 'complete_stream'):
            raise NotImplementedError(f"Gateway {type(self.adapter).__name__} does not support streaming")

        approximate_tokens = len(self.tokenizer.encode(self._content_to_count(messages)))
        logger.info(f"Requesting streaming llm response with approx {approximate_tokens} tokens")

        # Convert messages to serializable dict for audit
        messages_for_tracer = [m.model_dump() for m in messages]

        # Record LLM call in tracer
        tools_for_tracer = [{"name": t.name, "description": t.description} for t in
                            tools] if tools else None
        self.tracer.record_llm_call(
            self.model,
            messages_for_tracer,
            config.temperature,
            tools=tools_for_tracer,
            source=type(self),
            correlation_id=correlation_id
        )

        # Measure call duration for audit
        start_time = time.time()

        # Accumulate content and tool calls from stream
        accumulated_content = ""
        accumulated_tool_calls = []

        stream = self.adapter.complete_stream(
            model=self.model,
            messages=messages,
            tools=tools,
            config=config,
            temperature=config.temperature,
            num_ctx=config.num_ctx,
            num_predict=config.num_predict,
            max_tokens=config.max_tokens
        )

        for chunk in stream:
            # Handle content chunks
            if hasattr(chunk, 'content') and chunk.content:
                accumulated_content += chunk.content
                yield chunk.content

            # Handle tool calls if present
            if hasattr(chunk, 'tool_calls') and chunk.tool_calls:
                accumulated_tool_calls.extend(chunk.tool_calls)

        call_duration_ms = (time.time() - start_time) * 1000

        # Record LLM response in tracer
        tool_calls_for_tracer = [tc.model_dump() if hasattr(tc, 'model_dump') else tc for tc in
                                 accumulated_tool_calls] if accumulated_tool_calls else None
        self.tracer.record_llm_response(
            self.model,
            accumulated_content,
            tool_calls=tool_calls_for_tracer,
            call_duration_ms=call_duration_ms,
            source=type(self),
            correlation_id=correlation_id
        )

        # Process tool calls if any were accumulated
        if accumulated_tool_calls and tools is not None:
            logger.info("Tool call requested in streaming response")
            normalized_calls = [
                self._normalize_streamed_tool_call(tc) for tc in accumulated_tool_calls
            ]
            paired = self._dispatch_tool_batch(
                normalized_calls,
                tools,
                caller="LLMBroker.generate_stream",
                correlation_id=correlation_id,
            )

            if paired:
                for tool_call, outcome in paired:
                    messages.append(
                        LLMMessage(role=MessageRole.Assistant, tool_calls=[tool_call])
                    )
                    messages.append(
                        LLMMessage(
                            role=MessageRole.Tool,
                            content=self._serialize_outcome(outcome),
                            tool_calls=[tool_call],
                        )
                    )
                yield from self.generate_stream(
                    messages, tools,
                    config=config.model_copy(
                        update={"max_tool_iterations": config.max_tool_iterations - 1}
                    ),
                    correlation_id=correlation_id
                )
                return

    @staticmethod
    def _normalize_streamed_tool_call(tool_call):
        """Convert raw provider tool-call payloads into LLMToolCall objects."""
        if isinstance(tool_call, LLMToolCall):
            return tool_call
        if hasattr(tool_call, 'name'):
            tool_name = tool_call.name
            tool_arguments = tool_call.arguments
            tool_call_id = getattr(tool_call, 'id', None)
        else:
            tool_name = tool_call.function.name
            tool_arguments = tool_call.function.arguments
            tool_call_id = getattr(tool_call.function, 'id', None)
        return LLMToolCall(id=tool_call_id, name=tool_name, arguments=tool_arguments)

    def _dispatch_tool_batch(self, tool_calls, tools, caller, correlation_id):
        """
        Execute a batch of tool calls through the configured tool_runner.

        Returns a list of ``(tool_call, outcome)`` pairs in input order for
        the calls that resolved to a known tool. Unknown tool names are
        logged and omitted so the broker mirrors the prior warn-and-skip
        behaviour. Per-call tracer events are emitted for every dispatched
        outcome.
        """
        from mojentic.llm.tools.runner import ToolCallExecution as _ToolCallExecution

        dispatched = []
        executions = []
        for idx, tool_call in enumerate(tool_calls):
            if any(t.matches(tool_call.name) for t in tools):
                exec_id = getattr(tool_call, 'id', None) or f"call-{idx}"
                dispatched.append(tool_call)
                executions.append(
                    _ToolCallExecution(id=exec_id, name=tool_call.name, args=tool_call.arguments)
                )
            else:
                logger.warn('Function not found', function=tool_call.name)
                logger.info('Expected usage of missing function', expected_usage=tool_call)

        if not executions:
            return []

        outcomes = self.tool_runner.run_batch(executions, tools)
        if inspect.isawaitable(outcomes):
            outcomes = _run_async_outcomes(outcomes)
        paired = list(zip(dispatched, outcomes))
        for tool_call, outcome in paired:
            self.tracer.record_tool_call(
                tool_call.name,
                tool_call.arguments,
                outcome.result if outcome.ok else {"error": str(outcome.error)},
                caller=caller,
                call_duration_ms=outcome.duration_ms,
                source=type(self),
                correlation_id=correlation_id,
            )
            if outcome.ok:
                logger.info('Function output', output=outcome.result)
            else:
                logger.warn(
                    'Tool execution failed',
                    function=tool_call.name,
                    error=str(outcome.error),
                )
        return paired

    @staticmethod
    def _serialize_outcome(outcome) -> str:
        if outcome.ok:
            return json.dumps(outcome.result)
        return json.dumps({"error": str(outcome.error)})

    def _content_to_count(self, messages: List[LLMMessage]):
        content = ""
        for message in messages:
            if message.content:
                content += message.content
        return content

    def generate_object(self, messages: List[LLMMessage], object_model: Type[BaseModel],
                        config: Optional[CompletionConfig] = None,
                        temperature: Optional[float] = None, num_ctx: Optional[int] = None,
                        num_predict: Optional[int] = None, max_tokens: Optional[int] = None,
                        correlation_id: str = None) -> BaseModel:
        """
        Generate a structured response from the LLM and return it as an object.

        Parameters
        ----------
        messages : List[LLMMessage]
            A list of messages to send to the LLM.
        object_model : BaseModel
            The class of the model to use for the structured response data.
        config : Optional[CompletionConfig]
            Configuration object for LLM completion (recommended). If provided with individual
            kwargs, a DeprecationWarning is emitted.
        temperature : Optional[float]
            The temperature to use for the response. Deprecated: use config.
        num_ctx : Optional[int]
            The number of context tokens to use. Deprecated: use config.
        num_predict : Optional[int]
            The number of tokens to predict. Deprecated: use config.
        max_tokens : Optional[int]
            The maximum number of tokens to generate. Deprecated: use config.
        correlation_id : str
            UUID string that is copied from cause-to-affect for tracing events.

        Returns
        -------
        BaseModel
            An instance of the model class provided containing the structured response data.
        """
        # Handle config vs individual kwargs
        if config is not None and any(
                param is not None for param in [temperature, num_ctx, num_predict, max_tokens]):
            warnings.warn(
                "Both config and individual kwargs provided. Using config and ignoring kwargs. "
                "Individual kwargs are deprecated, use config=CompletionConfig(...) instead.",
                DeprecationWarning,
                stacklevel=2
            )
        elif config is None:
            # Build config from individual kwargs
            config = CompletionConfig(
                temperature=temperature if temperature is not None else 1.0,
                num_ctx=num_ctx if num_ctx is not None else 32768,
                num_predict=num_predict if num_predict is not None else -1,
                max_tokens=max_tokens if max_tokens is not None else 16384
            )
        approximate_tokens = len(self.tokenizer.encode(self._content_to_count(messages)))
        logger.info(f"Requesting llm response with approx {approximate_tokens} tokens")

        # Convert messages to serializable dict for audit
        messages_for_tracer = [m.model_dump() for m in messages]

        # Record LLM call in tracer
        self.tracer.record_llm_call(
            self.model,
            messages_for_tracer,
            config.temperature,
            tools=None,
            source=type(self),
            correlation_id=correlation_id
        )

        # Measure call duration for audit
        start_time = time.time()

        result = self.adapter.complete(model=self.model, messages=messages,
                                       object_model=object_model,
                                       config=config,
                                       temperature=config.temperature, num_ctx=config.num_ctx,
                                       num_predict=config.num_predict, max_tokens=config.max_tokens)

        call_duration_ms = (time.time() - start_time) * 1000

        # Record LLM response in tracer with object representation
        # Convert object to string for tracer
        object_str = str(result.object.model_dump()) if hasattr(result.object,
                                                                "model_dump") else str(
            result.object)
        self.tracer.record_llm_response(
            self.model,
            f"Structured response: {object_str}",
            call_duration_ms=call_duration_ms,
            source=type(self),
            correlation_id=correlation_id
        )

        return result.object


def _run_async_outcomes(awaitable):
    """
    Drive an async ToolRunner from a sync broker call site.

    When a caller pairs the sync LLMBroker with AsyncParallelToolRunner
    we need to drive the runner's coroutine here. ``asyncio.run`` is
    not safe to call from inside an existing event loop, so fall back
    to creating a dedicated loop in that case.
    """
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(awaitable)
    # We're already inside a running loop — drive the coroutine on a fresh loop
    # in a worker thread so we don't deadlock the outer one.
    import concurrent.futures

    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        return pool.submit(asyncio.run, awaitable).result()
