from mojentic.agents.base_llm_agent import BaseLLMAgent
from mojentic.llm import LLMBroker
from mojentic.llm.tools.date_resolver import ResolveDateTool


class DecisioningAgent(BaseLLMAgent):
    def __init__(self, llm: LLMBroker):
        super().__init__(llm,
                         "You are a task coordinator, who breaks down tasks into component steps to be performed by others.")
        self.tools = [ResolveDateTool()]