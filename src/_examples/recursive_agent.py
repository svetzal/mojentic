"""
Example script demonstrating how to use the simple recursive agent.
"""

import asyncio

from mojentic.agents import SimpleRecursiveAgent


async def demonstrate_async():
    """
    Demonstrate how to use the simple recursive agent asynchronously.
    """
    agent = SimpleRecursiveAgent(model_name="llama3.3-70b-32k", max_iterations=3)

    print("\n" + "=" * 80)
    print("SIMPLE RECURSIVE AGENT - ASYNCHRONOUS EXAMPLE")
    print("=" * 80)

    # Example 1: Using solve_problem_async with await
    problem1 = "What is the capital of France?"
    print(f"\nProblem (Async/Await): {problem1}")
    solution1 = await agent.solve(problem1)
    print(f"\nSolution: {solution1}")

    # Example 2: Using solve_problem_async with a callback
    problem2 = "What are the three primary colors?"
    print(f"\nProblem (Async with Callback): {problem2}")
    solution2 = await agent.solve(problem2)
    print(f"\nSolution: {solution2}")

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
