"""
Task list for the ephemeral task manager.

This module provides a class for managing a list of tasks with state transitions.
"""

from enum import Enum
from typing import List, Optional
from pydantic import BaseModel


class TaskStatus(str, Enum):
    """
    Enumeration of possible task statuses.

    Tasks follow a state machine that transitions from PENDING through IN_PROGRESS to COMPLETED.
    """
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"


class Task(BaseModel):
    """
    Represents a task with an identifier, description, and status.
    """
    id: int
    description: str
    status: TaskStatus = TaskStatus.PENDING


class EphemeralTaskList:
    """
    Manages a list of tasks for the ephemeral task manager.

    This class provides methods for adding, starting, completing, and listing tasks.
    Tasks follow a state machine that transitions from PENDING through IN_PROGRESS to COMPLETED.
    """

    def __init__(self):
        """
        Initialize an empty task list and ID counter.
        """
        self._tasks: List[Task] = []
        self._next_id: int = 1

    def _claim_next_id(self) -> int:
        """
        Claim the next available ID and increment the counter.

        Returns:
            The claimed ID
        """
        id = self._next_id
        self._next_id += 1
        return id

    def append_task(self, description: str) -> Task:
        """
        Add a new task to the end of the list.

        Args:
            description: The description of the task

        Returns:
            The newly created task with PENDING status
        """
        # Generate a new ID
        id = self._claim_next_id()

        task = Task(id=id, description=description, status=TaskStatus.PENDING)
        self._tasks.append(task)
        return task

    def prepend_task(self, description: str) -> Task:
        """
        Add a new task to the beginning of the list.

        Args:
            description: The description of the task

        Returns:
            The newly created task with PENDING status
        """
        # Generate a new ID
        id = self._claim_next_id()

        task = Task(id=id, description=description, status=TaskStatus.PENDING)
        self._tasks.insert(0, task)
        return task

    def insert_task_after(self, existing_task_id: int, description: str) -> Task:
        """
        Insert a new task after an existing task.

        Args:
            existing_task_id: The ID of the existing task after which to insert the new task
            description: The description of the new task

        Returns:
            The newly created task with PENDING status

        Raises:
            ValueError: If no task with the given ID exists
        """
        # Find the position of the existing task
        position = None
        for i, task in enumerate(self._tasks):
            if task.id == existing_task_id:
                position = i
                break

        if position is None:
            raise ValueError(f"No task with ID '{existing_task_id}' exists")

        # Generate a new ID
        id = self._claim_next_id()

        task = Task(id=id, description=description, status=TaskStatus.PENDING)
        self._tasks.insert(position + 1, task)
        return task

    def start_task(self, id: int) -> Task:
        """
        Start a task by changing its status from PENDING to IN_PROGRESS.

        Args:
            id: The ID of the task to start

        Returns:
            The started task

        Raises:
            ValueError: If no task with the given ID exists or if the task is not in PENDING status
        """
        task = self._get_task(id)

        if task.status != TaskStatus.PENDING:
            raise ValueError(f"Task '{id}' cannot be started because it is not in PENDING status")

        task.status = TaskStatus.IN_PROGRESS
        return task

    def complete_task(self, id: int) -> Task:
        """
        Complete a task by changing its status from IN_PROGRESS to COMPLETED.

        Args:
            id: The ID of the task to complete

        Returns:
            The completed task

        Raises:
            ValueError: If no task with the given ID exists or if the task is not in IN_PROGRESS status
        """
        task = self._get_task(id)

        if task.status != TaskStatus.IN_PROGRESS:
            raise ValueError(f"Task '{id}' cannot be completed because it is not in IN_PROGRESS status")

        task.status = TaskStatus.COMPLETED
        return task

    def list_tasks(self) -> List[Task]:
        """
        Get all tasks in the list.

        Returns:
            A list of all tasks
        """
        return self._tasks.copy()

    def clear_tasks(self) -> int:
        """
        Remove all tasks from the list.

        Returns:
            The number of tasks that were cleared
        """
        count = len(self._tasks)
        self._tasks = []
        return count

    def _get_task(self, id: int) -> Task:
        """
        Get a task by its ID.

        Args:
            id: The ID of the task to get

        Returns:
            The task with the given ID

        Raises:
            ValueError: If no task with the given ID exists
        """
        for task in self._tasks:
            if task.id == id:
                return task

        raise ValueError(f"No task with ID '{id}' exists")
