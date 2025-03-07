from typing import List

import structlog

from mojentic.llm import LLMBroker, ChatSession
from mojentic.llm.tools.llm_tool import LLMTool

logger = structlog.get_logger()


class IterativeProblemSolver:
    """An agent that solves problems iteratively using available tools.

    This solver breaks down complex problems into steps, using available tools to accomplish
    the task. It maintains context throughout the process and provides structured results.

    Attributes:
        user_request: The original request to be processed
        max_loops: Maximum number of iterations before giving up
        chat: The chat session maintaining conversation context

    The final result is formatted according to whether the task succeeded or failed:
    - For successful tasks:
        - Direct answer or solution
        - Relevant outputs and results
        - Concise, solution-focused response
    - For failed tasks:
        - Specific explanation of what couldn't be accomplished
        - Description of partial progress (if any)
        - Suggested alternatives (where applicable)

    The response maintains professionalism and focuses on outcomes rather than process.
    """
    user_request: str
    max_loops: int
    chat: ChatSession

    def __init__(self, llm: LLMBroker, user_request: str, available_tools: List[LLMTool], max_loops: int = 3):
        self.available_tools = available_tools
        self.user_request = user_request
        self.max_loops = max_loops
        self.chat = ChatSession(
            llm=llm,
            system_prompt="You are a helpful assistant, working on behalf of the user on a specific user request.",
            tools=available_tools,
        )

    def step(self) -> str:
        prompt = f"""
Given the user request:
{self.user_request}

Use the tools at your disposal to act on their request. You may wish to create a step-by-step plan for more complicated requests.

If you cannot provide an answer, say only "FAIL".
If you have the answer, say only "DONE".
"""
        return self.chat.send(prompt)

    def run(self):
        loops_remaining = self.max_loops

        while True:
            result = self.step()
            print(result)

            if "FAIL".lower() in result.lower():
                stop_message = f"Task failed: {result}"
                break
            elif "DONE".lower() in result.lower():
                stop_message = f"Task completed: {result}"
                break

            loops_remaining -= 1
            if loops_remaining == 0:
                stop_message = "Task failed: max loops reached"
                break

        print(stop_message)

        success = "DONE".lower() in result.lower()
        final_prompt = f"""
Given the original user request:
{self.user_request}

Your task has {"succeeded" if success else "failed"}. Please provide a final response following these guidelines:

1. Format your response in a clear, structured manner
2. If successful:
   - Provide the direct answer or solution
   - Include any relevant output or results
   - Keep it concise and focused on the solution
3. If failed:
   - Explain what specifically couldn't be accomplished
   - If possible, describe what partial progress was made
   - Suggest alternative approaches if applicable

Remember:
- Focus only on the final outcome
- Do not describe the process or steps taken
- Do not include any meta-commentary about the response itself
- Be direct and professional in your response
"""
        result = self.chat.send(final_prompt)

        return result
