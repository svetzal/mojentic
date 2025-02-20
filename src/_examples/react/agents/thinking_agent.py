from mojentic.agents.base_llm_agent import BaseLLMAgent
from mojentic.llm import LLMBroker
from mojentic.llm.gateways.models import LLMMessage
from mojentic.llm.tools.date_resolver import ResolveDateTool

from ..models.base import Plan, ThoughtActionObservation
from ..models.events import InvokeThinking, InvokeDecisioning


class ThinkingAgent(BaseLLMAgent):
    def __init__(self, llm: LLMBroker):
        super().__init__(llm,
                         "You are a task coordinator, who breaks down tasks into component steps to be performed by others.")
        self.tools = [ResolveDateTool()]

    def receive_event(self, event: InvokeThinking):
        prompt = self.prompt(event)
        print(f"\n\n#######################################\n{prompt}\n#######################################\n\n")
        plan: Plan = self.llm.generate_object([LLMMessage(content=prompt)], object_model=Plan)
        print(f"\n\n#######################################\n{plan}\n#######################################\n\n")
        event.context.plan = plan
        event.context.history.append(ThoughtActionObservation(thought="I have no plan yet.", action="Create a plan.",
                                                              observation="Ready for next step."))
        return InvokeDecisioning(source=type(self), context=event.context)

    def prompt(self, event: InvokeThinking):
        user_query = f"The user has asked us to answer the following query:\n> {event.context.user_query}\n"

        plan = "You have not yet made a plan.\n"
        if event.context.plan.steps:
            plan = "Current plan:\n"
            plan += "\n".join(f"- {step}" for step in event.context.plan.steps)
            plan += "\n\n"

        history = "No steps have yet been taken.\n"
        if event.context.history:
            history = "What's been done so far':\n"
            history += "\n".join(
                f"{i + 1}.\n    Thought: {step.thought}\n    Action: {step.action}\n    Observation: {step.observation}"
                for i, step in enumerate(event.context.history))
            history += "\n\n"

        tools = ""
        if self.tools:
            tools += "Tools available:\n"
            for tool in self.tools:
                tools += f"- {tool.descriptor["function"]["name"]}: {tool.descriptor["function"]["description"]}\n"

        return f"""
You are to solve a problem by reasoning and acting on the information you have. Here is the current context:

Current Context:
{user_query}{plan}{history}

{tools}

Your Instructions:
Given our context and what we've done so far, and the tools available, create a step-by-step plan to answer the query. 
        """.strip()