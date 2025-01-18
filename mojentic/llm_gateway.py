from typing import List

from ollama import Message, chat, Options
from pydantic import BaseModel


class LLMGateway():
    def __init__(self, model: str):
        self.model = model

    def generate(self, messages: List[Message], response_model: BaseModel) -> BaseModel:
        response = chat(
            model=self.model,
            messages=messages,
            options=Options(temperature=0.5, num_ctx=32768),
            format=response_model.model_json_schema()
        )
        return response_model.model_validate_json(response.message.content)
