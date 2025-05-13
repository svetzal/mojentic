from unittest.mock import Mock

import pytest

from mojentic.llm.tools.ephemeral_task_manager.append_task_tool import AppendTaskTool
from mojentic.llm.tools.ephemeral_task_manager.ephemeral_task_list import EphemeralTaskList, Task, TaskStatus


@pytest.fixture
def mock_task_list():
    mock = Mock(spec=EphemeralTaskList)
    return mock


@pytest.fixture
def append_task_tool(mock_task_list):
    return AppendTaskTool(task_list=mock_task_list)


class DescribeAppendTaskTool:
    def should_call_append_task_with_description(self, append_task_tool, mock_task_list):
        mock_task = Task(id=1, description="Test task", status=TaskStatus.PENDING)
        mock_task_list.append_task.return_value = mock_task

        append_task_tool.run(description="Test task")

        mock_task_list.append_task.assert_called_once_with(description="Test task")

    def should_handle_error_when_append_task_fails(self, append_task_tool, mock_task_list):
        mock_task_list.append_task.side_effect = ValueError("Test error")

        append_task_tool.run(description="Test task")

        mock_task_list.append_task.assert_called_once_with(description="Test task")
