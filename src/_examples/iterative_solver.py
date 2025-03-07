import logging

from mojentic.agents.iterative_problem_solver import IterativeProblemSolver

logging.basicConfig(level=logging.WARN)

from mojentic.llm.tools.date_resolver import ResolveDateTool
from mojentic.llm.tools.ask_user_tool import AskUserTool
from mojentic.llm import LLMBroker


def main():
    # llm = LLMBroker(model="MFDoom/deepseek-r1-tool-calling:14b")
    # llm = LLMBroker(model="qwen2.5:14b")
    llm = LLMBroker(model="qwq")
    # llm = LLMBroker(model="llama3.3-70b-32k")

    user_request = """
I want to launch a new brand of eco-friendly home cleaning products. Can you create a marketing plan detailing target demographics, promotional channels, a rough budget breakdown, and a timeline of major milestones? Please include example social media copy, key talking points for a press release, and measurable success criteria for each channel.
    """.strip()

    # user_request = "What's the date next Friday?"

    ooda = IterativeProblemSolver(
        llm=llm,
        user_request=user_request,
        available_tools=[AskUserTool(), ResolveDateTool()],
        max_loops=5
    )
    result = ooda.run()
    print(f"User Request:\n{user_request}\n")
    print(f"Agent Response:\n{result}\n")


if __name__ == "__main__":
    main()
