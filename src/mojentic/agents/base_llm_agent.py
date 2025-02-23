import json
from typing import Annotated, Optional, Type, List

from pydantic import BaseModel, Field

from mojentic.agents.base_agent import BaseAgent
from mojentic.context.shared_working_memory import SharedWorkingMemory
from mojentic.llm.gateways.models import LLMMessage, MessageRole
from mojentic.llm.llm_broker import LLMBroker
from mojentic.llm.tools.llm_tool import LLMTool


class BaseLLMAgent(BaseAgent):
    llm: LLMBroker
    behaviour: Annotated[str, "The personality and behavioural traits of the agent."]

    def __init__(self, llm: LLMBroker, behaviour: str = "You are a helpful assistant.",
                 tools: Optional[List[LLMTool]] = None, response_model: Optional[Type[BaseModel]] = None):
        super().__init__()
        self.llm = llm
        self.behaviour = behaviour
        self.response_model = response_model
        self.tools = tools or []

    def _create_initial_messages(self):
        return [
            LLMMessage(role=MessageRole.System, content=self.behaviour),
        ]

    def add_tool(self, tool):
        self.tools.append(tool)

    def generate_response(self, content):
        messages = self._create_initial_messages()
        messages.append(LLMMessage(content=content))

        if self.response_model is not None:
            response = self.llm.generate_object(messages, object_model=self.response_model)
        else:
            response = self.llm.generate(messages, tools=self.tools)

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
            LLMMessage(content=f"This is what you remember:\n{json.dumps(self.memory.get_working_memory(), indent=2)}"
                               f"\n\nRemember anything new you learn by storing it to your working memory in your response."),
            LLMMessage(role=MessageRole.User, content=self.instructions),
        ])
        return messages

    def generate_response(self, content):
        class ResponseWithMemory(self.response_model):
            memory: dict = Field(self.memory.get_working_memory(),
                                 description="Add anything new that you have learned here.")

        messages = self._create_initial_messages()
        messages.extend([
            LLMMessage(content=content),
        ])
        response = self.llm.generate_object(
            messages=messages,
            object_model=ResponseWithMemory
        )
        self.memory.merge_to_working_memory(response.memory)

        d = response.model_dump()
        del d["memory"]

        return self.response_model.model_validate(d)
