"""Tool execution agent for the ReAct pattern.

This agent handles the actual execution of tools and captures the results.
"""
from typing import List

from mojentic.agents.base_agent import BaseAgent
from mojentic.event import Event

from ..models.base import ThoughtActionObservation
from ..models.events import FailureOccurred, InvokeDecisioning, InvokeToolCall


class ToolCallAgent(BaseAgent):
    """Agent responsible for executing tool calls.

    This agent receives tool call events, executes the specified tool,
    and updates the context with the results before continuing to the
    decisioning phase.
    """

    def receive_event(self, event: Event) -> List[Event]:
        """Execute a tool and update the context.

        Args:
            event: The tool call event containing the tool and arguments.

        Returns:
            List containing InvokeDecisioning event with updated context,
            or FailureOccurred on error.
        """
        if not isinstance(event, InvokeToolCall):
            return []

        try:
            tool = event.tool
            tool_name = tool.name
            arguments = event.tool_arguments

            print(f"\nExecuting tool: {tool_name}")
            print(f"Arguments: {arguments}")

            # Execute the tool using call_tool method
            result = tool.call_tool(
                correlation_id=event.correlation_id,
                **arguments
            )

            print(f"Result: {result}")

            # Extract the text content from the result
            result_text = result
            if isinstance(result, dict) and "content" in result:
                # Extract text from content array
                content_items = result["content"]
                if content_items and isinstance(content_items, list):
                    result_text = content_items[0].get("text", str(result))

            # Add to history
            event.context.history.append(
                ThoughtActionObservation(
                    thought=event.thought,
                    action=f"Called {tool_name} with {arguments}",
                    observation=str(result_text)
                )
            )

            # Continue to decisioning
            return [InvokeDecisioning(
                source=type(self),
                context=event.context,
                correlation_id=event.correlation_id
            )]

        except Exception as e:
            import traceback
            traceback.print_exc()
            return [FailureOccurred(
                source=type(self),
                context=event.context,
                reason=f"Tool execution failed: {str(e)}",
                correlation_id=event.correlation_id
            )]
