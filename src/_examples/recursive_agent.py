"""
Example script demonstrating how to use the SimpleRecursiveAgent.

This script shows how to create and use a SimpleRecursiveAgent to solve problems
asynchronously, including running multiple problem-solving tasks concurrently.
"""

import asyncio

from mojentic.agents import SimpleRecursiveAgent
from mojentic.llm import LLMBroker


async def demonstrate_async():
    """
    Demonstrate how to use the SimpleRecursiveAgent asynchronously.

    This function shows three different ways to use the agent:
    1. Basic async/await usage
    2. Using the agent with event handling
    3. Running multiple problem-solving tasks concurrently
    """
    # Initialize the LLM broker with your preferred model
    llm = LLMBroker(model="llama3.3-70b-32k")

    # Create the agent with a maximum of 3 iterations
    agent = SimpleRecursiveAgent(llm=llm, max_iterations=3)

    print("\n" + "=" * 80)
    print("SIMPLE RECURSIVE AGENT - ASYNCHRONOUS EXAMPLE")
    print("=" * 80)

    # Example 1: Basic async/await usage
    problem1 = "What is the capital of France?"
    print(f"\nProblem (Basic Async/Await): {problem1}")
    solution1 = await agent.solve(problem1)
    print(f"\nSolution: {solution1}")

    # Example 2: Using the agent with event subscription
    problem2 = "What are the three primary colors?"
    print(f"\nProblem (With Event Handling): {problem2}")

    # Set up event handlers for monitoring the solution process
    from mojentic.agents.simple_recursive_agent import ProblemSolvedEvent, IterationCompletedEvent

    # Define event handlers
    def on_iteration_completed(event):
        print(f"  Iteration {event.state.iteration} completed")

    def on_problem_solved(event):
        print(f"  Problem solved after {event.state.iteration} iterations")

    # Subscribe to events
    unsubscribe_iteration = agent.emitter.subscribe(IterationCompletedEvent, on_iteration_completed)
    unsubscribe_solved = agent.emitter.subscribe(ProblemSolvedEvent, on_problem_solved)

    # Solve the problem
    solution2 = await agent.solve(problem2)
    print(f"\nSolution: {solution2}")

    # Unsubscribe from events
    unsubscribe_iteration()
    unsubscribe_solved()

    # Example 3: Running multiple async tasks concurrently
    print("\nRunning multiple problems concurrently:")
    problems = [
        "What is the Pythagorean theorem?",
        "Explain the concept of recursion in programming."
    ]

    async def solve_and_print(problem):
        print(f"\nStarted solving: {problem}")
        solution = await agent.solve(problem)
        print(f"\nSolution for '{problem}':\n{solution}")
        return solution

    # Create tasks for all problems and run them concurrently
    tasks = [solve_and_print(problem) for problem in problems]
    solutions = await asyncio.gather(*tasks)

    print("\nAll concurrent problems have been solved!")


if __name__ == "__main__":
    # Run the async example
    asyncio.run(demonstrate_async())
