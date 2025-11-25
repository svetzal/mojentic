"""Planning agent for the ReAct pattern.

This agent creates structured plans for solving user queries.
"""
from typing import List

from mojentic.agents.base_llm_agent import BaseLLMAgent
from mojentic.event import Event
from mojentic.llm import LLMBroker
from mojentic.llm.gateways.models import LLMMessage
from mojentic.llm.tools.date_resolver import ResolveDateTool
from mojentic.utils import format_block

from ..formatters import format_available_tools, format_current_context
from ..models.base import Plan, ThoughtActionObservation
from ..models.events import FailureOccurred, InvokeDecisioning, InvokeThinking


class ThinkingAgent(BaseLLMAgent):
    """Agent responsible for creating plans in the ReAct loop.

    This agent analyzes the user query and available tools to create
    a step-by-step plan for answering the query.
    """

    def __init__(self, llm: LLMBroker):
        """Initialize the thinking agent.

        Args:
            llm: The LLM broker to use for generating plans.
        """
        super().__init__(
            llm,
            ("You are a task coordinator, "
             "who breaks down tasks into component steps "
             "to be performed by others.")
        )
        self.tools = [ResolveDateTool()]

    def receive_event(self, event: Event) -> List[Event]:
        """Process a thinking event and generate a plan.

        Args:
            event: The thinking event containing current context.

        Returns:
            List containing InvokeDecisioning event with updated plan,
            or FailureOccurred on error.
        """
        if not isinstance(event, InvokeThinking):
            return []

        try:
            prompt = self.prompt(event)
            print(format_block(prompt))

            plan: Plan = self.llm.generate_object(
                [LLMMessage(content=prompt)],
                object_model=Plan
            )
            print(format_block(str(plan)))

            # Update context with new plan
            event.context.plan = plan

            # Add planning step to history
            event.context.history.append(
                ThoughtActionObservation(
                    thought="I need to create a plan to solve this query.",
                    action="Created a step-by-step plan.",
                    observation=f"Plan has {len(plan.steps)} steps."
                )
            )

            return [InvokeDecisioning(
                source=type(self),
                context=event.context,
                correlation_id=event.correlation_id
            )]

        except Exception as e:
            return [FailureOccurred(
                source=type(self),
                context=event.context,
                reason=f"Error during planning: {str(e)}",
                correlation_id=event.correlation_id
            )]

    def prompt(self, event: InvokeThinking):
        """Generate the prompt for the planning LLM.

        Args:
            event: The thinking event containing current context.

        Returns:
            The formatted prompt string.
        """
        return f"""
You are to solve a problem by reasoning and acting on the information you have. Here is the current context:

{format_current_context(event.context)}
{format_available_tools(self.tools)}

Your Instructions:
Given our context and what we've done so far, and the tools available, create a step-by-step plan to answer the query.
Each step should be concrete and actionable. Consider which tools you'll need to use.
        """.strip()
