"""ReAct Pattern Example.

This example demonstrates a Reasoning and Acting (ReAct) loop where agents
iteratively plan, decide, act, and summarize to answer user queries.

The ReAct pattern consists of:
1. Thinking Agent - Creates plans
2. Decisioning Agent - Decides next actions
3. Tool Call Agent - Executes tools
4. Summarization Agent - Generates final answers
"""
from _examples.react.agents.decisioning_agent import DecisioningAgent
from _examples.react.agents.summarization_agent import SummarizationAgent
from _examples.react.agents.thinking_agent import ThinkingAgent
from _examples.react.agents.tool_call_agent import ToolCallAgent
from _examples.react.models.base import CurrentContext
from _examples.react.models.events import (
    FailureOccurred,
    FinishAndSummarize,
    InvokeDecisioning,
    InvokeThinking,
    InvokeToolCall,
)
from mojentic import Dispatcher, Router
from mojentic.agents.output_agent import OutputAgent
from mojentic.llm import LLMBroker


def main():
    """Run the ReAct pattern example."""
    # Initialize LLM broker - using qwen3:32b as it's widely available
    llm = LLMBroker("qwen3:32b")
    # Alternative models (uncomment if available):
    # llm = LLMBroker("deepseek-r1:70b")
    # llm = LLMBroker("qwen3:8b")

    # Create agents
    thinking_agent = ThinkingAgent(llm)
    decisioning_agent = DecisioningAgent(llm)
    tool_call_agent = ToolCallAgent()
    summarization_agent = SummarizationAgent(llm)
    output_agent = OutputAgent()

    # Configure router - maps event types to agent handlers
    router = Router({
        InvokeThinking: [thinking_agent, output_agent],
        InvokeDecisioning: [decisioning_agent, output_agent],
        InvokeToolCall: [tool_call_agent, output_agent],
        FinishAndSummarize: [summarization_agent, output_agent],
        FailureOccurred: [output_agent],
    })

    # Create dispatcher
    dispatcher = Dispatcher(router)

    # Create initial context
    initial_context = CurrentContext(
        user_query="What is the date next Friday?"
    )

    # Start the ReAct loop
    print("\n" + "=" * 80)
    print("Starting ReAct Pattern Example")
    print("=" * 80)
    print(f"User Query: {initial_context.user_query}")
    print("=" * 80 + "\n")

    # Create and dispatch initial thinking event
    initial_event = InvokeThinking(
        source=type(main),
        context=initial_context
    )

    dispatcher.dispatch(initial_event)

    print("\n" + "=" * 80)
    print("ReAct Pattern Example Complete")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    main()
