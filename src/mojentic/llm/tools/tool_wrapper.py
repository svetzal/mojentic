"""
Not sure about this module right now. There are a couple ways to do this.
"""
from typing import Any
from mojentic.llm.tools.llm_tool import LLMTool
from mojentic.agents.base_llm_agent import BaseLLMAgent
from mojentic.llm.gateways.models import LLMMessage, MessageRole


class ToolWrapper(LLMTool):
    def __init__(self, agent: BaseLLMAgent, name: str, description: str):
        self.agent = agent
        self.tool_name = name  # agent.__class__.__name__.lower()
        self.tool_description = description

    def run(self, input: str) -> str:
        messages = self.agent._create_initial_messages()
        messages.append(LLMMessage(content=input))
        return self.agent.llm.generate(messages, tools=self.agent.tools)

    @property
    def descriptor(self):
        return {
            "type": "function",
            "function": {
                "name": self.tool_name,
                "description": self.tool_description,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "input": {
                            "type": "string",
                            "description": "Instructions for this agent.",
                        }
                    },
                    "required": ["input"],
                    "additionalProperties": False
                }
            }
        }
