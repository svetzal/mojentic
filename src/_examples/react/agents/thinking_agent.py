from mojentic.agents.base_llm_agent import BaseLLMAgent
from mojentic.llm import LLMBroker
from mojentic.llm.gateways.models import LLMMessage
from mojentic.llm.tools.date_resolver import ResolveDateTool
from mojentic.utils import format_block
from ..formatters import format_current_context, format_available_tools

from ..models.base import Plan, ThoughtActionObservation
from ..models.events import InvokeThinking, InvokeDecisioning


class ThinkingAgent(BaseLLMAgent):
    def __init__(self, llm: LLMBroker):
        super().__init__(llm,
                         "You are a task coordinator, who breaks down tasks into component steps to be performed by others.")
        self.tools = [ResolveDateTool()]

    def receive_event(self, event: InvokeThinking):
        prompt = self.prompt(event)
        print(format_block(prompt))
        plan: Plan = self.llm.generate_object([LLMMessage(content=prompt)], object_model=Plan)
        print(format_block(str(plan)))
        event.context.plan = plan
        event.context.history.append(ThoughtActionObservation(thought="I have no plan yet.", action="Create a plan.",
                                                              observation="Ready for next step."))
        return InvokeDecisioning(source=type(self), context=event.context)

    def prompt(self, event: InvokeThinking):
        return f"""
You are to solve a problem by reasoning and acting on the information you have. Here is the current context:

{format_current_context(event.context)}
{format_available_tools(self.tools)}

Your Instructions:
Given our context and what we've done so far, and the tools available, create a step-by-step plan to answer the query. 
        """.strip()
