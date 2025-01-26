import json
from typing import Annotated, Optional, Type

from ollama import Message
from pydantic import BaseModel, Field

from mojentic.base_agent import BaseAgent
from mojentic.llm.llm_broker import LLMBroker
from mojentic.shared_working_memory import SharedWorkingMemory


class BaseLLMAgent(BaseAgent):
    llm: LLMBroker
    behaviour: Annotated[str, "The personality and behavioural traits of the agent."]

    def __init__(self, llm: LLMBroker, behaviour: str = "You are a helpful assistant.", response_model: Optional[Type[BaseModel]] = None):
        super().__init__()
        self.llm = llm
        self.behaviour = behaviour
        self.response_model = response_model
        self.tools = []

    def _create_initial_messages(self):
        return [
            {'role': 'system', 'content': self.behaviour},
        ]

    def add_tool(self, tool):
        self.tools.append(tool)

    def generate_response(self, content):
        messages = self._create_initial_messages()
        messages.extend([
            {"role": "user", "content": content},
        ])

        response = self.llm.generate(messages, response_model=self.response_model, tools=self.tools)

        return response


class BaseLLMAgentWithMemory(BaseLLMAgent):
    instructions: Annotated[str, "The instructions for the agent to follow when receiving events."]

    def __init__(self, llm: LLMBroker, memory: SharedWorkingMemory, behaviour: str, instructions: str,
                 response_model: BaseModel):
        super().__init__(llm, behaviour)
        self.instructions = instructions
        self.memory = memory
        self.response_model = response_model

    def _create_initial_messages(self):
        messages = super()._create_initial_messages()
        messages.extend([
            {
                "role": "user",
                "content": f"This is what you remember:\n{json.dumps(self.memory.get_working_memory(), indent=2)}\n\nAdd anything new you learn to your working memory."
            },
            {"role": "user", "content": self.instructions},
        ])
        return messages

    def generate_response(self, content):
        class ResponseWithMemory(self.response_model):
            memory: dict = Field(self.memory.get_working_memory(),
                                 description="Add anything new that you have learned here.")

        messages = self._create_initial_messages()
        messages.extend([
            {"role": "user", "content": content},
        ])
        response = self.llm.generate_object(
            messages=messages,
            object_model=ResponseWithMemory
        )
        self.memory.merge_to_working_memory(response.memory)

        d = response.model_dump()
        del d["memory"]

        return self.response_model.model_validate(d)
