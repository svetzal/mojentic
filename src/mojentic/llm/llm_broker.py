import structlog
from pydantic import BaseModel

from mojentic.llm.adapters import LLMGateway, OllamaGateway
from mojentic.llm.tokenizer_gateway import TokenizerGateway

logger = structlog.get_logger()


class LLMBroker():
    adapter: LLMGateway
    tokenizer: TokenizerGateway
    model: str

    def __init__(self, model: str, adapter: LLMGateway = None, tokenizer: TokenizerGateway = None):
        self.model = model
        if tokenizer is None:
            self.tokenizer = TokenizerGateway()
        else:
            self.tokenizer = tokenizer
        if adapter is None:
            self.adapter = OllamaGateway()
        else:
            self.adapter = adapter

    def generate(self, messages, response_model=None, tools=None, temperature=1.0, num_ctx=32768, num_predict=-1):
        approximate_tokens = len(self.tokenizer.encode("".join([message['content'] for message in messages])))
        logger.info(f"Requesting llm response with approx {approximate_tokens} tokens")

        result = self.adapter.complete(
            model=self.model,
            messages=messages,
            response_model=response_model,
            tools=tools,
            temperature=temperature,
            num_ctx=num_ctx,
            num_predict=num_predict)

        if result['tool_calls'] and tools is not None:
            logger.info("Tool call requested")
            for requested_tool in result['tool_calls']:
                if function_descriptor := next((t for t in tools if
                                                t['descriptor']['function']['name'] == requested_tool.function.name),
                                               None):
                    logger.info('Calling function', function=requested_tool.function.name)
                    logger.info('Arguments:', arguments=requested_tool.function.arguments)
                    python_function = function_descriptor["python_function"]
                    output = python_function(**requested_tool.function.arguments)
                    logger.info('Function output', output=output)
                    messages.append({'role': 'assistant', 'content': result['content']})
                    messages.append({'role': 'tool', 'content': str(output), 'name': requested_tool.function.name})
                    return self.generate(messages, tools, temperature, num_ctx, num_predict)
                else:
                    logger.warn('Function not found', function=requested_tool.function.name)
                    logger.info('Expected usage of missing function', expected_usage=requested_tool)
                    # raise Exception('Unknown tool function requested:', requested_tool.function.name)

        return result['content']

    def generate_model(self, messages, response_model, temperature=1.0, num_ctx=32768, num_predict=-1) -> BaseModel:
        approximate_tokens = len(self.tokenizer.encode("".join([message['content'] for message in messages])))
        logger.info(f"Requesting llm response with approx {approximate_tokens} tokens")
        return self.adapter.complete_with_object(
            model=self.model,
            messages=messages,
            response_model=response_model,
            temperature=temperature,
            num_ctx=num_ctx,
            num_predict=num_predict
        )
