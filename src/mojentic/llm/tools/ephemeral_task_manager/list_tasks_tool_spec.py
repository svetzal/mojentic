from unittest.mock import Mock

import pytest

from mojentic.llm.tools.ephemeral_task_manager.ephemeral_task_list import EphemeralTaskList, Task, TaskStatus
from mojentic.llm.tools.ephemeral_task_manager.list_tasks_tool import ListTasksTool


@pytest.fixture
def mock_task_list():
    mock = Mock(spec=EphemeralTaskList)
    return mock


@pytest.fixture
def list_tasks_tool(mock_task_list):
    return ListTasksTool(task_list=mock_task_list)


class DescribeListTasksTool:
    def should_call_list_tasks(self, list_tasks_tool, mock_task_list):
        mock_tasks = [
            Task(id=1, description="Task 1", status=TaskStatus.PENDING),
            Task(id=2, description="Task 2", status=TaskStatus.IN_PROGRESS),
            Task(id=3, description="Task 3", status=TaskStatus.COMPLETED)
        ]
        mock_task_list.list_tasks.return_value = mock_tasks

        list_tasks_tool.run()

        mock_task_list.list_tasks.assert_called_once()

    def should_handle_empty_list(self, list_tasks_tool, mock_task_list):
        mock_task_list.list_tasks.return_value = []

        list_tasks_tool.run()

        mock_task_list.list_tasks.assert_called_once()
