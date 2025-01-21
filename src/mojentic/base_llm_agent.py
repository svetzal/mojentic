from typing import Annotated

from ollama import Message

from _examples.simple_llm import ResponseModel
from mojentic.base_agent import BaseAgent
from mojentic.llm_gateway import LLMGateway


class BaseLLMAgent(BaseAgent):
    llm: LLMGateway
    behaviour: Annotated[str, "The personality and behavioural traits of the agent."]
    instructions: Annotated[str, "The instructions for the agent to follow when receiving events."]

    def __init__(self, llm: LLMGateway, behaviour: str, instructions: str):
        super().__init__()
        self.llm = llm
        self.behaviour = behaviour
        self.instructions = instructions

    def _create_initial_messages(self):
        messages = [
            Message(role="system", content=self.behaviour),
            Message(role="user", content=self.instructions),
        ]
        return messages

    def generate_response(self, content):
        messages = self._create_initial_messages()
        messages.extend([
            Message(role="user", content=content),
        ])
        response = self.llm.generate_model(
            messages=messages,
            response_model=ResponseModel
        )
        return response

