"""
Example script demonstrating how to use the IterativeProblemSolver.

This script shows how to create and run an IterativeProblemSolver to solve a simple
date-related query using the ResolveDateTool.
"""

import logging

logging.basicConfig(level=logging.WARN)

from mojentic.agents.iterative_problem_solver import IterativeProblemSolver
from mojentic.llm.tools.date_resolver import ResolveDateTool
from mojentic.llm.tools.ask_user_tool import AskUserTool
from mojentic.llm import LLMBroker


def main():
    # Initialize the LLM broker with your preferred model
    # Uncomment one of the following lines or modify as needed:
    # llm = LLMBroker(model="llama3.3-70b-32k")  # Ollama model
    # llm = LLMBroker(model="gpt-4o")  # OpenAI model
    llm = LLMBroker(model="qwq")  # Default model for example

    # Define a simple user request
    user_request = "What's the date next Friday?"

    # Create the problem solver with necessary tools
    solver = IterativeProblemSolver(
        llm=llm,
        available_tools=[AskUserTool(), ResolveDateTool()],
        max_iterations=5
    )

    # Run the solver and get the result
    result = solver.solve(user_request)

    # Display the results
    print(f"User Request:\n{user_request}\n")
    print(f"Agent Response:\n{result}\n")


if __name__ == "__main__":
    main()
