"""
Tool for appending a new task to the end of the ephemeral task manager list.
"""

from typing import Dict

from mojentic.llm.tools.llm_tool import LLMTool
from mojentic.llm.tools.ephemeral_task_manager.ephemeral_task_list import EphemeralTaskList


class AppendTaskTool(LLMTool):
    """
    Tool for appending a new task to the end of the ephemeral task manager list.
    """

    def __init__(self, task_list: EphemeralTaskList):
        """
        Initialize the tool with a shared task list.

        Args:
            task_list: The shared task list to use
        """
        self._task_list = task_list

    def run(self, description: str) -> Dict[str, str]:
        """
        Append a new task to the end of the list.

        Args:
            description: The description of the task

        Returns:
            A dictionary with the result of the operation

        Raises:
            ValueError: If there's an error adding the task
        """
        try:
            task = self._task_list.append_task(description=description)
            return {
                "id": task.id,
                "description": task.description,
                "status": task.status.value,
                "summary": f"Task '{task.id}' appended successfully"
            }
        except ValueError as e:
            return {
                "error": str(e),
                "summary": f"Failed to append task: {str(e)}"
            }

    @property
    def descriptor(self):
        """
        Get the descriptor for the tool.

        Returns:
            The descriptor dictionary
        """
        return {
            "type": "function",
            "function": {
                "name": "append_task",
                "description": "Append a new task to the end of the task list with a description. The task will start with 'pending' status.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "description": {
                            "type": "string",
                            "description": "The description of the task"
                        }
                    },
                    "required": ["description"],
                    "additionalProperties": False
                }
            }
        }
