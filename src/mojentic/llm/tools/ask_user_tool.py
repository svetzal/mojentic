from mojentic.llm.tools.llm_tool import LLMTool


class AskUserTool(LLMTool):
    def run(self, user_request: str) -> str:
        print(f"\n\n\nI NEED YOUR HELP!\n{user_request}")
        return input(f"Your response: ")

    @property
    def descriptor(self):
        return {
            "type": "function",
            "function": {
                "name": "ask_user",
                "description": "If you do not know how to proceed, ask the user a question, or ask them for help or to do something for you.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "user_request": {
                            "type": "string",
                            "description": "The question you need the user to answer, or the task you need the user to do for you."
                        }
                    },
                    "required": ["user_request"]
                },
            },
        }