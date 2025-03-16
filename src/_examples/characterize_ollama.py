from ollama import chat
from pydantic import BaseModel, Field

from mojentic.llm.gateways.models import LLMMessage, MessageRole
from mojentic.llm.gateways.ollama import OllamaGateway
from mojentic.llm.tools.date_resolver import ResolveDateTool


def check_ollama_gateway():
    gateway = OllamaGateway()

    class Feeling(BaseModel):
        label: str = Field(..., description="The label describing the feeling.")

    response = gateway.complete(
        model="llama3.2:1b",
        messages=[LLMMessage(content="Hello, how are you?")],
        object_model=Feeling,
        temperature=1.0,
        num_ctx=32768,
        num_predict=-1
    )
    print(response)


def check_tools_call():
    response = chat(
        model="llama3.3-70b-32k",
        messages=[
            # {
            #     'role': 'user',
            #     'content': "What is the date on Friday?"
            # },
            {
                "role": "user",
                "content": "What is the date on Friday?"
            },
            # {
            #     'role': 'assistant',
            #     'content': '',
            #     'tool_calls': [
            #         {
            #             'function': {
            #                 'name': 'resolve_date',
            #                 'arguments': {
            #                     'relative_date_found': 'Friday'
            #                 }
            #             }
            #         }
            #     ]
            # },
            {
                "role": "assistant",
                "content": "",
                "tool_calls": {
                    "type": "function",
                    "function": {
                        "name": "resolve_date",
                        "arguments": {
                            "relative_date_found": "Friday"
                        }
                    }
                }
            },
            # {
            #     "role": "tool",
            #     "content": "{\"relative_date\": \"Friday\", \"resolved_date\": \"2025-01-31\"}"
            # }
            {
                'role': 'tool',
                'content': '{"relative_date": "Friday", "resolved_date": "2025-01-31"}',
            }
        ],
        tools=[ResolveDateTool().descriptor]
    )
    print(response)
    # print(response.message.model_dump_json(indent=2))
    # print(response.message.tool_calls[0])
    # print(resolve_date_tool['python_function'](relative_date_found='Friday'))


check_ollama_gateway()
# check_tools_call()
