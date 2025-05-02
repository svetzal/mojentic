"""
Tool for prepending a new task to the beginning of the ephemeral task manager list.
"""

from typing import Dict

from mojentic.llm.tools.llm_tool import LLMTool
from mojentic.llm.tools.ephemeral_task_manager.ephemeral_task_list import EphemeralTaskList


class PrependTaskTool(LLMTool):
    """
    Tool for prepending a new task to the beginning of the ephemeral task manager list.
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
        Prepend a new task to the beginning of the list.

        Args:
            description: The description of the task

        Returns:
            A dictionary with the result of the operation

        Raises:
            ValueError: If there's an error adding the task
        """
        try:
            task = self._task_list.prepend_task(description=description)
            return {
                "id": task.id,
                "description": task.description,
                "status": task.status.value,
                "summary": f"Task '{task.id}' prepended successfully"
            }
        except ValueError as e:
            return {
                "error": str(e),
                "summary": f"Failed to prepend task: {str(e)}"
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
                "name": "prepend_task",
                "description": "Prepend a new task to the beginning of the task list with a description. The task will start with 'pending' status.",
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