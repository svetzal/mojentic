from mojentic.llm.tools.llm_tool import LLMTool


class TellUserTool(LLMTool):
    def run(self, message: str) -> str:
        print(f"\n\n\nMESSAGE FROM ASSISTANT:\n{message}")
        return "Message delivered to user."

    @property
    def descriptor(self):
        return {
            "type": "function",
            "function": {
                "name": "tell_user",
                "description": "Display a message to the user without expecting a response. Use this to send important intermediate information to the user as you work on completing their request.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "message": {
                            "type": "string",
                            "description": "The important message you want to display to the user."
                        }
                    },
                    "required": ["message"]
                },
            },
        }