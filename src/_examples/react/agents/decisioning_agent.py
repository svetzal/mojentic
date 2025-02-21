from mojentic.utils import format_block
from ..formatters import format_current_context, format_available_tools
from ..models.events import InvokeDecisioning, InvokeToolCall
from mojentic.agents.base_llm_agent import BaseLLMAgent
from mojentic.llm import LLMBroker
from mojentic.llm.tools.date_resolver import ResolveDateTool


class DecisioningAgent(BaseLLMAgent):
    def __init__(self, llm: LLMBroker):
        super().__init__(llm,
                         "You are a careful decision maker, weighing the situation and making the best choice based on the information available.")
        self.tools = [ResolveDateTool()]

        def receive_event(self, event: InvokeDecisioning):
            prompt = self.prompt(event)
            print(format_block(prompt))
            tool_to_call = self.tools[0]
            return [InvokeToolCall(source=type(self), context=event.context, tool=tool_to_call)]

        def prompt(self, event: InvokeDecisioning):
            prompt = f"""
You are to solve a problem by reasoning and acting on the information you have. Here is the current context:

{format_current_context(event.context)}
{format_available_tools(self.tools)}

Your Instructions:
Given our context and what we've done so far, and the tools available, create a step-by-step plan to answer the query. 
            """.strip()

            return prompt