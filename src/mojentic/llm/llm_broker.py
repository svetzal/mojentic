import json
import time
from typing import List, Optional, Type

import structlog
from pydantic import BaseModel

from mojentic.audit.audit_system import AuditSystem
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
    audit_system: Optional[AuditSystem]

    def __init__(self, model: str, gateway: Optional[LLMGateway] = None, tokenizer: Optional[TokenizerGateway] = None,
                 audit_system: Optional[AuditSystem] = None):
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
        audit_system
            Optional audit system to record LLM calls and responses.
        """
        self.model = model
        self.audit_system = audit_system
        
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
        
        # Convert messages to serializable dict for audit
        messages_for_audit = [m.dict() for m in messages]
        
        # Record LLM call in audit if available
        if self.audit_system:
            tools_for_audit = [{"name": t.name, "description": t.description} for t in tools] if tools else None
            self.audit_system.record_llm_call(
                self.model, 
                messages_for_audit, 
                temperature,
                tools=tools_for_audit,
                source=type(self)
            )
        
        # Measure call duration for audit
        start_time = time.time()
        
        result: LLMGatewayResponse = self.adapter.complete(
            model=self.model,
            messages=messages,
            tools=tools,
            temperature=temperature,
            num_ctx=num_ctx,
            num_predict=num_predict)
        
        call_duration_ms = (time.time() - start_time) * 1000
        
        # Record LLM response in audit if available
        if self.audit_system:
            tool_calls_for_audit = [tc.dict() for tc in result.tool_calls] if result.tool_calls else None
            self.audit_system.record_llm_response(
                self.model,
                result.content,
                tool_calls=tool_calls_for_audit,
                call_duration_ms=call_duration_ms,
                source=type(self)
            )

        if result.tool_calls and tools is not None:
            logger.info("Tool call requested")
            for tool_call in result.tool_calls:
                if tool := next((t for t in tools if
                                 t.matches(tool_call.name)),
                                None):
                    logger.info('Calling function', function=tool_call.name)
                    logger.info('Arguments:', arguments=tool_call.arguments)
                    
                    # Record tool call in audit if available
                    if self.audit_system:
                        # Get the arguments before calling the tool
                        tool_arguments = tool_call.arguments
                    
                    # Call the tool
                    output = tool.run(**tool_call.arguments)
                    
                    # Record tool call result in audit if available
                    if self.audit_system:
                        self.audit_system.record_tool_call(
                            tool_call.name,
                            tool_arguments,
                            output,
                            caller="LLMBroker",
                            source=type(self)
                        )
                    
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
        
        # Convert messages to serializable dict for audit
        messages_for_audit = [m.dict() for m in messages]
        
        # Record LLM call in audit if available
        if self.audit_system:
            self.audit_system.record_llm_call(
                self.model, 
                messages_for_audit, 
                temperature,
                tools=None,
                source=type(self)
            )
        
        # Measure call duration for audit
        start_time = time.time()
        
        result = self.adapter.complete(model=self.model, messages=messages, object_model=object_model,
                                       temperature=temperature, num_ctx=num_ctx, num_predict=num_predict)
        
        call_duration_ms = (time.time() - start_time) * 1000
        
        # Record LLM response in audit with object representation if available
        if self.audit_system:
            # Convert object to string for audit
            object_str = str(result.object.dict()) if hasattr(result.object, "dict") else str(result.object)
            self.audit_system.record_llm_response(
                self.model,
                f"Structured response: {object_str}",
                call_duration_ms=call_duration_ms,
                source=type(self)
            )
        
        return result.object
        
    def set_audit_system(self, audit_system: Optional[AuditSystem]) -> None:
        """
        Set or update the audit system used by this LLMBroker.
        
        Parameters
        ----------
        audit_system : AuditSystem or None
            The audit system to use, or None to disable auditing.
        """
        self.audit_system = audit_system
