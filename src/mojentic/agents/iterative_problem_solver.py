from typing import List

import structlog

from mojentic.llm import LLMBroker, ChatSession
from mojentic.llm.tools.llm_tool import LLMTool

logger = structlog.get_logger()


class IterativeProblemSolver:
    """An agent that iteratively attempts to solve a problem using available tools.

    This solver uses a chat-based approach to break down and solve complex problems.
    It will continue attempting to solve the problem until it either succeeds,
    fails explicitly, or reaches the maximum number of iterations.

    Attributes
    ----------
    user_request : str
        The original request or problem to be solved
    max_iterations : int
        Maximum number of attempts to solve the problem
    chat : ChatSession
        The chat session used for problem-solving interaction
    """

    user_request: str
    max_iterations: int
    chat: ChatSession

    def __init__(self, llm: LLMBroker, user_request: str, available_tools: List[LLMTool], max_iterations: int = 3):
        """Initialize the IterativeProblemSolver.

        Parameters
        ----------
        llm : LLMBroker
            The language model broker to use for generating responses
        user_request : str
            The problem or request to be solved
        available_tools : List[LLMTool]
            List of tools that can be used to solve the problem
        max_iterations : int, optional
            Maximum number of attempts to solve the problem, by default 3
        """
        self.available_tools = available_tools
        self.user_request = user_request
        self.max_iterations = max_iterations
        self.chat = ChatSession(
            llm=llm,
            system_prompt="You are a helpful assistant, working on behalf of the user on a specific user request.",
            tools=available_tools,
        )

    def step(self) -> str:
        """Execute a single problem-solving step.

        This method sends a prompt to the chat session asking it to work on the user's request
        using available tools. The response should indicate success ("DONE") or failure ("FAIL").

        Returns
        -------
        str
            The response from the chat session, indicating the step's outcome
        """
        prompt = f"""
Given the user request:
{self.user_request}

Use the tools at your disposal to act on their request. You may wish to create a step-by-step plan for more complicated requests.

If you cannot provide an answer, say only "FAIL".
If you have the answer, say only "DONE".
"""
        return self.chat.send(prompt)

    def run(self):
        """Execute the problem-solving process.

        This method runs the iterative problem-solving process, continuing until one of
        these conditions is met:
        - The task is completed successfully ("DONE")
        - The task fails explicitly ("FAIL")
        - The maximum number of iterations is reached

        Returns
        -------
        str
            A summary of the final result, excluding the process details
        """
        iterations_remaining = self.max_iterations

        while True:
            result = self.step()

            if "FAIL".lower() in result.lower():
                logger.info("Task failed", user_request=self.user_request, result=result)
                break
            elif "DONE".lower() in result.lower():
                logger.info("Task completed", user_request=self.user_request, result=result)
                break

            iterations_remaining -= 1
            if iterations_remaining == 0:
                logger.info("Max iterations reached", max_iterations=self.max_iterations,
                            user_request=self.user_request, result=result)
                break

        result = self.chat.send(
            "Summarize the final result, and only the final result, without commenting on the process by which you achieved it.")

        return result
