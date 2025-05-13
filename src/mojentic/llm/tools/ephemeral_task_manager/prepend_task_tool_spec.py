from unittest.mock import Mock

import pytest

from mojentic.llm.tools.ephemeral_task_manager.ephemeral_task_list import EphemeralTaskList, Task, TaskStatus
from mojentic.llm.tools.ephemeral_task_manager.prepend_task_tool import PrependTaskTool


@pytest.fixture
def mock_task_list():
    mock = Mock(spec=EphemeralTaskList)
    return mock


@pytest.fixture
def prepend_task_tool(mock_task_list):
    return PrependTaskTool(task_list=mock_task_list)


class DescribePrependTaskTool:
    def should_call_prepend_task_with_description(self, prepend_task_tool, mock_task_list):
        mock_task = Task(id=1, description="Test task", status=TaskStatus.PENDING)
        mock_task_list.prepend_task.return_value = mock_task

        prepend_task_tool.run(description="Test task")

        mock_task_list.prepend_task.assert_called_once_with(description="Test task")

    def should_handle_error_when_prepend_task_fails(self, prepend_task_tool, mock_task_list):
        mock_task_list.prepend_task.side_effect = ValueError("Test error")

        prepend_task_tool.run(description="Test task")

        mock_task_list.prepend_task.assert_called_once_with(description="Test task")
