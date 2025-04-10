from typing import Optional

from pydantic import BaseModel

from mojentic.llm.tools.llm_tool import LLMTool


class SimpleResponse(BaseModel):
    """Simple response model for testing object validation"""
    answer: str
    confidence: Optional[float] = None


class SimpleTool(LLMTool):
    """Simple tool for testing tool calls"""
    name = "simple_calculator"
    description = "A simple calculator that can add two numbers"

    @property
    def descriptor(self):
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "a": {
                            "type": "number",
                            "description": "The first number"
                        },
                        "b": {
                            "type": "number",
                            "description": "The second number"
                        }
                    },
                    "required": ["a", "b"]
                }
            }
        }

    def execute(self, **kwargs):
        a = kwargs.get("a", 0)
        b = kwargs.get("b", 0)
        return {"result": a + b}
