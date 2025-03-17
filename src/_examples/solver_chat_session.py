import logging
from typing import List

from mojentic.agents import IterativeProblemSolver
from mojentic.llm.tools.date_resolver import ResolveDateTool
from mojentic.llm.tools.llm_tool import LLMTool

logging.basicConfig(level=logging.WARN)

from mojentic.llm import LLMBroker, ChatSession


class IterativeProblemSolverTool(LLMTool):
    def __init__(self, llm: LLMBroker, tools: List[LLMTool]):
        self.llm = llm
        self.tools = tools

    def run(self, problem_to_solve: str):
        solver = IterativeProblemSolver(llm=self.llm, available_tools=self.tools)
        return solver.solve(problem_to_solve)

    @property
    def descriptor(self):
        return {
            "type": "function",
            "function": {
                "name": "iterative_problem_solver",
                "description": "Iteratively solve a complex multi-step problem using available tools.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "problem_to_solve": {
                            "type": "string",
                            "description": "The problem or request to be solved.",
                        }
                    },
                    "required": ["problem_to_solve"],
                    "additionalProperties": False
                }
            }
        }


def main():
    # llm = LLMBroker(model="MFDoom/deepseek-r1-tool-calling:14b")
    # llm = LLMBroker(model="qwen2.5:14b")
    # llm = LLMBroker(model="qwen2.5:14b")
    # llm = LLMBroker(model="qwen2.5:7b")
    llm = LLMBroker(model="qwq")
    # llm = LLMBroker(model="qwq:32b-fp16")
    # llm = LLMBroker(model="llama3.3-70b-32k")

    tools = [
        ResolveDateTool(),
        IterativeProblemSolverTool(llm=llm, tools=[ResolveDateTool()])
    ]

    chat_session = ChatSession(llm, tools=[IterativeProblemSolverTool(llm=llm, tools=[ResolveDateTool()])])

    while True:
        query = input("Query: ")
        if not query:
            break
        else:
            response = chat_session.send(query)
            print(response)


if __name__ == "__main__":
    main()
