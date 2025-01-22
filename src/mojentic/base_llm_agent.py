import json
from typing import Annotated

from ollama import Message
from pydantic import BaseModel, Field

from mojentic.base_agent import BaseAgent
from mojentic.llm_gateway import LLMGateway
from mojentic.shared_working_memory import SharedWorkingMemory


class BaseLLMAgent(BaseAgent):
    llm: LLMGateway
    behaviour: Annotated[str, "The personality and behavioural traits of the agent."]
    instructions: Annotated[str, "The instructions for the agent to follow when receiving events."]

    def __init__(self, llm: LLMGateway, memory: SharedWorkingMemory, behaviour: str, instructions: str, response_model: BaseModel):
        super().__init__()
        self.llm = llm
        self.memory = memory
        self.behaviour = behaviour
        self.instructions = instructions
        self.response_model = response_model

    def _create_initial_messages(self):
        messages = [
            Message(role="system", content=self.behaviour),
            Message(role="user", content=self.instructions),
            Message(role="user", content=f"This is what you remember:\n{json.dumps(self.memory.get_working_memory(), indent=2)}\n\nAdd anything new you learn to your working memory."),
        ]
        return messages

    def generate_response(self, content):
        class ResponseWithMemory(self.response_model):
            memory: dict = Field(self.memory.get_working_memory(), description="Add anything new that you have learned here.")

        messages = self._create_initial_messages()
        messages.extend([
            Message(role="user", content=content),
        ])
        response = self.llm.generate_model(
            messages=messages,
            response_model=ResponseWithMemory
        )
        self.memory.merge_to_working_memory(response.memory)

        d = response.model_dump()
        del d["memory"]

        return self.response_model.model_validate(d)

