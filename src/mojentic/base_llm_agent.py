from typing import Annotated

from mojentic.base_agent import BaseAgent
from mojentic.llm_gateway import LLMGateway


class BaseLLMAgent(BaseAgent):
    llm: LLMGateway
    behaviour: Annotated[str, "The personality and behavioural traits of the agent."]
    instructions: Annotated[str, "The instructions for the agent to follow when receiving events."]

    def __init__(self, llm: LLMGateway):
        super().__init__()
        self.llm = llm
