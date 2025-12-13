"""Summarization agent for the ReAct pattern.

This agent generates the final answer based on accumulated context.
"""
from typing import List

from mojentic.agents.base_llm_agent import BaseLLMAgent
from mojentic.event import Event
from mojentic.llm import LLMBroker
from mojentic.llm.gateways.models import LLMMessage
from mojentic.utils import format_block

from ..formatters import format_current_context
from ..models.events import FailureOccurred, FinishAndSummarize


class SummarizationAgent(BaseLLMAgent):
    """Agent responsible for generating the final answer.

    This agent reviews the context, plan, and history to synthesize
    a complete answer to the user's original query.
    """

    def __init__(self, llm: LLMBroker):
        """Initialize the summarization agent.

        Args:
            llm: The LLM broker to use for generating summaries.
        """
        super().__init__(
            llm,
            ("You are a helpful assistant who provides clear, "
             "accurate answers based on the information gathered.")
        )

    def receive_event(self, event: Event) -> List[Event]:
        """Generate a final answer based on the context.

        Args:
            event: The finish event containing the complete context.

        Returns:
            Empty list (terminal event) or list with FailureOccurred on error.
        """
        if not isinstance(event, FinishAndSummarize):
            return []

        try:
            prompt = self.prompt(event)
            print(format_block(prompt))

            response = self.llm.generate([LLMMessage(content=prompt)])

            print("\n" + "=" * 80)
            print("FINAL ANSWER:")
            print("=" * 80)
            print(response)
            print("=" * 80 + "\n")

            # This is a terminal event - return empty list to stop the loop
            return []

        except Exception as e:
            return [FailureOccurred(
                source=type(self),
                context=event.context,
                reason=f"Error during summarization: {str(e)}",
                correlation_id=event.correlation_id
            )]

    def prompt(self, event: FinishAndSummarize):
        """Generate the prompt for the summarization LLM.

        Args:
            event: The finish event containing the complete context.

        Returns:
            The formatted prompt string.
        """
        return f"""
Based on the following context, provide a clear and concise answer to the user's query.

{format_current_context(event.context)}

Your task:
Review what we've learned and provide a direct answer to: "{event.context.user_query}"

Be specific and use the information gathered during our process.
        """.strip()
