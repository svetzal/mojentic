"""
Tool for clearing all tasks from the ephemeral task manager.
"""

from typing import Dict

from mojentic.llm.tools.llm_tool import LLMTool
from mojentic.llm.tools.ephemeral_task_manager.ephemeral_task_list import EphemeralTaskList


class ClearTasksTool(LLMTool):
    """
    Tool for clearing all tasks from the ephemeral task manager.
    """

    def __init__(self, task_list: EphemeralTaskList):
        """
        Initialize the tool with a shared task list.

        Args:
            task_list: The shared task list to use
        """
        self._task_list = task_list

    def run(self) -> Dict[str, str]:
        """
        Remove all tasks from the list.

        Returns:
            A dictionary with the result of the operation
        """
        count = self._task_list.clear_tasks()
        return {
            "count": str(count),
            "summary": f"Cleared {count} tasks from the list"
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
                "name": "clear_tasks",
                "description": "Remove all tasks from the task list.",
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "additionalProperties": False
                }
            }
        }
