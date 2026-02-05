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
from mojentic.tracer.tracer_system import TracerSystem

logger = structlog.get_logger()


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

    def __init__(self, model: str, gateway: Optional[LLMGateway] = None,
                 tokenizer: Optional[TokenizerGateway] = None,
                 tracer: Optional[TracerSystem] = None):
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
            for tool_call in result.tool_calls:
                if tool := next((t for t in tools if
                                 t.matches(tool_call.name)),
                                None):
                    logger.info('Calling function', function=tool_call.name)
                    logger.info('Arguments:', arguments=tool_call.arguments)

                    # Get the arguments before calling the tool
                    tool_arguments = tool_call.arguments

                    # Measure tool execution time
                    tool_start_time = time.time()

                    # Call the tool
                    output = tool.run(**tool_call.arguments)

                    tool_duration_ms = (time.time() - tool_start_time) * 1000

                    # Record tool call in tracer
                    self.tracer.record_tool_call(
                        tool_call.name,
                        tool_arguments,
                        output,
                        caller="LLMBroker",
                        call_duration_ms=tool_duration_ms,
                        source=type(self),
                        correlation_id=correlation_id
                    )

                    logger.info('Function output', output=output)
                    messages.append(LLMMessage(role=MessageRole.Assistant, tool_calls=[tool_call]))
                    messages.append(
                        LLMMessage(role=MessageRole.Tool, content=json.dumps(output),
                                   tool_calls=[tool_call]))
                    # {'role': 'tool', 'content': str(output), 'name': tool_call.name,
                    # 'tool_call_id': tool_call.id})
                    return self.generate(messages, tools, config=config,
                                         correlation_id=correlation_id)
                else:
                    logger.warn('Function not found', function=tool_call.name)
                    logger.info('Expected usage of missing function', expected_usage=tool_call)
                    # raise Exception('Unknown tool function requested:',
                    # requested_tool.function.name)

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
            for tool_call in accumulated_tool_calls:
                # Handle both LLMToolCall objects and raw tool call data
                if hasattr(tool_call, 'name'):
                    tool_name = tool_call.name
                    tool_arguments = tool_call.arguments
                else:
                    # Handle ollama's tool call format
                    tool_name = tool_call.function.name
                    tool_arguments = tool_call.function.arguments

                if tool := next((t for t in tools if t.matches(tool_name)), None):
                    logger.info('Calling function', function=tool_name)
                    logger.info('Arguments:', arguments=tool_arguments)

                    # Measure tool execution time
                    tool_start_time = time.time()

                    # Call the tool
                    output = tool.run(**tool_arguments)

                    tool_duration_ms = (time.time() - tool_start_time) * 1000

                    # Record tool call in tracer
                    self.tracer.record_tool_call(
                        tool_name,
                        tool_arguments,
                        output,
                        caller="LLMBroker.generate_stream",
                        call_duration_ms=tool_duration_ms,
                        source=type(self),
                        correlation_id=correlation_id
                    )

                    logger.info('Function output', output=output)

                    # Convert to LLMToolCall if needed, preserving the ID if it exists
                    if not isinstance(tool_call, LLMToolCall):
                        # Extract ID if available from the tool_call object
                        tool_call_id = None
                        if hasattr(tool_call, 'id'):
                            tool_call_id = tool_call.id
                        elif hasattr(tool_call, 'function') and hasattr(tool_call.function, 'id'):
                            tool_call_id = tool_call.function.id

                        tool_call = LLMToolCall(id=tool_call_id, name=tool_name, arguments=tool_arguments)

                    messages.append(LLMMessage(role=MessageRole.Assistant, tool_calls=[tool_call]))
                    messages.append(
                        LLMMessage(role=MessageRole.Tool, content=json.dumps(output),
                                   tool_calls=[tool_call]))

                    # Recursively stream the response after tool execution
                    yield from self.generate_stream(
                        messages, tools, config=config, correlation_id=correlation_id
                    )
                    return  # Exit after recursive call
                else:
                    logger.warn('Function not found', function=tool_name)

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
