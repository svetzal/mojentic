"""
Tool for completing a task in the ephemeral task manager.
"""

from typing import Dict

from mojentic.llm.tools.llm_tool import LLMTool
from mojentic.llm.tools.ephemeral_task_manager.ephemeral_task_list import EphemeralTaskList


class CompleteTaskTool(LLMTool):
    """
    Tool for completing a task in the ephemeral task manager.

    This tool changes a task's status from IN_PROGRESS to COMPLETED.
    """

    def __init__(self, task_list: EphemeralTaskList):
        """
        Initialize the tool with a shared task list.

        Args:
            task_list: The shared task list to use
        """
        self._task_list = task_list

    def run(self, id: int) -> Dict[str, str]:
        """
        Complete a task by changing its status from IN_PROGRESS to COMPLETED.

        Args:
            id: The ID of the task to complete

        Returns:
            A dictionary with the result of the operation

        Raises:
            ValueError: If no task with the given ID exists or if the task is not in IN_PROGRESS status
        """
        try:
            # Convert id to int if it's a string
            task_id = int(id) if isinstance(id, str) else id
            task = self._task_list.complete_task(id=task_id)
            return {
                "id": task.id,
                "description": task.description,
                "status": task.status.value,
                "summary": f"Task '{id}' completed successfully"
            }
        except ValueError as e:
            return {
                "error": str(e),
                "summary": f"Failed to complete task: {str(e)}"
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
                "name": "complete_task",
                "description": "Complete a task by changing its status from IN_PROGRESS to COMPLETED.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "id": {
                            "type": "integer",
                            "description": "The ID of the task to complete"
                        }
                    },
                    "required": ["id"],
                    "additionalProperties": False
                }
            }
        }
