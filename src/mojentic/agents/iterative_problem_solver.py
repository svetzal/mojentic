from typing import List

import structlog

from mojentic.llm import LLMBroker, ChatSession
from mojentic.llm.tools.llm_tool import LLMTool

logger = structlog.get_logger()


class IterativeProblemSolver:
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

        result = self.chat.send("Summarize the final result, and only the final result, without commenting on the process by which you achieved it.")

        return result
