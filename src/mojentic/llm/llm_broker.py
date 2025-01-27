from typing import List

import structlog
from pydantic import BaseModel

from mojentic.llm.gateways.models import MessageRole, LLMMessage, LLMGatewayResponse
from mojentic.llm.gateways.ollama import OllamaGateway
from mojentic.llm.gateways.llm_gateway import LLMGateway
from mojentic.llm.gateways.tokenizer_gateway import TokenizerGateway

logger = structlog.get_logger()


class LLMBroker():
    adapter: LLMGateway
    tokenizer: TokenizerGateway
    model: str

    def __init__(self, model: str, gateway: LLMGateway = None, tokenizer: TokenizerGateway = None):
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
                if function_descriptor := next((t for t in tools if
                                                t['descriptor']['function']['name'] == tool_call.name),
                                               None):
                    logger.info('Calling function', function=tool_call.name)
                    logger.info('Arguments:', arguments=tool_call.arguments)
                    python_function = function_descriptor["python_function"]
                    output = python_function(**tool_call.arguments)
                    logger.info('Function output', output=output)
                    messages.append(LLMMessage(role=MessageRole.Assistant, tool_calls=[tool_call]))
                    messages.append(LLMMessage(role=MessageRole.Tool, content=output, tool_calls=[tool_call]))
                    # {'role': 'tool', 'content': str(output), 'name': tool_call.name, 'tool_call_id': tool_call.id})
                    return self.generate(messages, tools, temperature, num_ctx, num_predict)
                else:
                    logger.warn('Function not found', function=tool_call.name)
                    logger.info('Expected usage of missing function', expected_usage=tool_call)
                    # raise Exception('Unknown tool function requested:', requested_tool.function.name)

        return result.content

    def _content_to_count(self, messages):
        content = ""
        for message in messages:
            if 'content' in message and message['content']:
                content += message['content']
        return content

    def generate_object(self, messages, object_model, temperature=1.0, num_ctx=32768, num_predict=-1) -> BaseModel:
        approximate_tokens = len(self.tokenizer.encode(self._content_to_count(messages)))
        logger.info(f"Requesting llm response with approx {approximate_tokens} tokens")
        result = self.adapter.complete(model=self.model, messages=messages, object_model=object_model,
                                       temperature=temperature, num_ctx=num_ctx, num_predict=num_predict)
        return result.object
