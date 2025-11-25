"""Decision-making agent for the ReAct pattern.

This agent evaluates the current context and decides on the next action to take.
"""
from typing import List

from pydantic import BaseModel, Field

from mojentic.agents.base_llm_agent import BaseLLMAgent
from mojentic.event import Event
from mojentic.llm import LLMBroker
from mojentic.llm.gateways.models import LLMMessage
from mojentic.llm.tools.date_resolver import ResolveDateTool
from mojentic.utils import format_block

from ..formatters import format_available_tools, format_current_context
from ..models.base import NextAction
from ..models.events import (
    FailureOccurred,
    FinishAndSummarize,
    InvokeDecisioning,
    InvokeThinking,
    InvokeToolCall,
)


class DecisionResponse(BaseModel):
    """Structured response from the decisioning agent."""

    thought: str = Field(
        ...,
        description="The reasoning behind the decision"
    )
    next_action: NextAction = Field(
        ...,
        description="What should happen next: PLAN, ACT, or FINISH"
    )
    tool_name: str | None = Field(
        None,
        description="Name of tool to use if next_action is ACT"
    )
    tool_arguments: dict = Field(
        default_factory=dict,
        description=("Arguments for the tool if next_action is ACT. "
                     "IMPORTANT: Use the exact parameter names from the tool's descriptor. "
                     "For resolve_date, use 'relative_date_found' not 'date_text'.")
    )


class DecisioningAgent(BaseLLMAgent):
    """Agent responsible for deciding the next action in the ReAct loop.

    This agent evaluates the current context, plan, and history to determine
    whether to continue planning, take an action, or finish and summarize.
    """

    MAX_ITERATIONS = 10

    def __init__(self, llm: LLMBroker):
        """Initialize the decisioning agent.

        Args:
            llm: The LLM broker to use for generating decisions.
        """
        super().__init__(
            llm,
            ("You are a careful decision maker, "
             "weighing the situation and making the best choice "
             "based on the information available.")
        )
        self.tools = [ResolveDateTool()]

    def receive_event(self, event: Event) -> List[Event]:
        """Process a decisioning event and determine the next action.

        Args:
            event: The decisioning event containing current context.

        Returns:
            List containing one of: InvokeToolCall, FinishAndSummarize,
            InvokeThinking, or FailureOccurred event.
        """
        if not isinstance(event, InvokeDecisioning):
            return []

        # Check iteration limit
        if event.context.iteration >= self.MAX_ITERATIONS:
            return [FailureOccurred(
                source=type(self),
                context=event.context,
                reason=f"Maximum iterations ({self.MAX_ITERATIONS}) exceeded",
                correlation_id=event.correlation_id
            )]

        # Increment iteration counter
        event.context.iteration += 1

        prompt = self.prompt(event)
        print(format_block(prompt))

        try:
            decision = self.llm.generate_object(
                [LLMMessage(content=prompt)],
                object_model=DecisionResponse
            )
            print(format_block(f"Decision: {decision}"))

            # Route based on decision
            if decision.next_action == NextAction.FINISH:
                return [FinishAndSummarize(
                    source=type(self),
                    context=event.context,
                    thought=decision.thought,
                    correlation_id=event.correlation_id
                )]

            if decision.next_action == NextAction.ACT:
                if not decision.tool_name:
                    return [FailureOccurred(
                        source=type(self),
                        context=event.context,
                        reason="ACT decision made but no tool specified",
                        correlation_id=event.correlation_id
                    )]

                # Find the requested tool
                tool = next(
                    (t for t in self.tools
                     if t.descriptor["function"]["name"] == decision.tool_name),
                    None
                )

                if not tool:
                    return [FailureOccurred(
                        source=type(self),
                        context=event.context,
                        reason=f"Tool '{decision.tool_name}' not found",
                        correlation_id=event.correlation_id
                    )]

                return [InvokeToolCall(
                    source=type(self),
                    context=event.context,
                    thought=decision.thought,
                    action=NextAction.ACT,
                    tool=tool,
                    tool_arguments=decision.tool_arguments,
                    correlation_id=event.correlation_id
                )]

            # PLAN action - go back to thinking
            return [InvokeThinking(
                source=type(self),
                context=event.context,
                correlation_id=event.correlation_id
            )]

        except Exception as e:
            return [FailureOccurred(
                source=type(self),
                context=event.context,
                reason=f"Error during decision making: {str(e)}",
                correlation_id=event.correlation_id
            )]

    def prompt(self, event: InvokeDecisioning):
        """Generate the prompt for the decision-making LLM.

        Args:
            event: The decisioning event containing current context.

        Returns:
            The formatted prompt string.
        """
        return f"""
You are to solve a problem by reasoning and acting on the information you have. Here is the current context:

{format_current_context(event.context)}
{format_available_tools(self.tools)}

Your Instructions:
Review the current plan and history. Decide what to do next:

1. PLAN - If the plan is incomplete or needs refinement
2. ACT - If you should take an action using one of the available tools
3. FINISH - If you have enough information to answer the user's query

If you choose ACT, specify which tool to use and what arguments to pass.
Think carefully about whether each step in the plan has been completed.
        """.strip()
