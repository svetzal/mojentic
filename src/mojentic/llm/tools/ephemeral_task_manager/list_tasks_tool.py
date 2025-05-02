"""
Tool for listing all tasks in the ephemeral task manager.
"""

from typing import Dict, List

from mojentic.llm.tools.ephemeral_task_manager.ephemeral_task_list import EphemeralTaskList, Task
from mojentic.llm.tools.llm_tool import LLMTool


class ListTasksTool(LLMTool):
    """
    Tool for listing all tasks in the ephemeral task manager.
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
        Get all tasks in the list.

        Returns:
            A dictionary with the result of the operation
        """
        tasks = self._task_list.list_tasks()

        # Format tasks as a string for the summary
        task_list_str = self._format_tasks(tasks)

        return {
            "count": str(len(tasks)),
            "tasks": task_list_str,
            "summary": f"Found {len(tasks)} tasks\n\n{task_list_str}"
        }

    def _format_tasks(self, tasks: List[Task]) -> str:
        """
        Format a list of tasks as a string.

        Args:
            tasks: The list of tasks to format

        Returns:
            A formatted string representation of the tasks
        """
        if not tasks:
            return "No tasks found."

        result = [f"{task.id}. {task.description} ({task.status.value})"
                  for i, task in enumerate(tasks)]

        return "\n".join(result)

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
                "name": "list_tasks",
                "description": "List all tasks in the task list.",
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "additionalProperties": False
                }
            }
        }
