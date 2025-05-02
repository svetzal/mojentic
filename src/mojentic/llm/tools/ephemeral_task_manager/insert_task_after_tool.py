"""
Tool for inserting a new task after an existing task in the ephemeral task manager list.
"""

from typing import Dict

from mojentic.llm.tools.llm_tool import LLMTool
from mojentic.llm.tools.ephemeral_task_manager.ephemeral_task_list import EphemeralTaskList


class InsertTaskAfterTool(LLMTool):
    """
    Tool for inserting a new task after an existing task in the ephemeral task manager list.
    """

    def __init__(self, task_list: EphemeralTaskList):
        """
        Initialize the tool with a shared task list.

        Args:
            task_list: The shared task list to use
        """
        self._task_list = task_list

    def run(self, existing_task_id: int, description: str) -> Dict[str, str]:
        """
        Insert a new task after an existing task.

        Args:
            existing_task_id: The ID of the existing task after which to insert the new task
            description: The description of the new task

        Returns:
            A dictionary with the result of the operation

        Raises:
            ValueError: If no task with the given ID exists
        """
        try:
            # Convert existing_task_id to int if it's a string
            task_id = int(existing_task_id) if isinstance(existing_task_id, str) else existing_task_id
            task = self._task_list.insert_task_after(existing_task_id=task_id, description=description)
            return {
                "id": task.id,
                "description": task.description,
                "status": task.status.value,
                "summary": f"Task '{task.id}' inserted after task '{existing_task_id}' successfully"
            }
        except ValueError as e:
            return {
                "error": str(e),
                "summary": f"Failed to insert task: {str(e)}"
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
                "name": "insert_task_after",
                "description": "Insert a new task after an existing task in the task list. The task will start with 'pending' status.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "existing_task_id": {
                            "type": "integer",
                            "description": "The ID of the existing task after which to insert the new task"
                        },
                        "description": {
                            "type": "string",
                            "description": "The description of the new task"
                        }
                    },
                    "required": ["existing_task_id", "description"],
                    "additionalProperties": False
                }
            }
        }
