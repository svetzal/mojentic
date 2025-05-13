from unittest.mock import Mock

import pytest

from mojentic.llm.tools.ephemeral_task_manager.ephemeral_task_list import EphemeralTaskList, Task, TaskStatus
from mojentic.llm.tools.ephemeral_task_manager.start_task_tool import StartTaskTool


@pytest.fixture
def mock_task_list():
    mock = Mock(spec=EphemeralTaskList)
    return mock


@pytest.fixture
def start_task_tool(mock_task_list):
    return StartTaskTool(task_list=mock_task_list)


class DescribeStartTaskTool:
    def should_call_start_task_with_correct_id(self, start_task_tool, mock_task_list):
        mock_task = Task(id=1, description="Test task", status=TaskStatus.IN_PROGRESS)
        mock_task_list.start_task.return_value = mock_task

        start_task_tool.run(id=1)

        mock_task_list.start_task.assert_called_once_with(id=1)

    def should_convert_string_id_to_int(self, start_task_tool, mock_task_list):
        mock_task = Task(id=1, description="Test task", status=TaskStatus.IN_PROGRESS)
        mock_task_list.start_task.return_value = mock_task

        start_task_tool.run(id="1")

        mock_task_list.start_task.assert_called_once_with(id=1)

    def should_handle_error_when_start_task_fails(self, start_task_tool, mock_task_list):
        error_message = "Task '1' cannot be started because it is not in PENDING status"
        mock_task_list.start_task.side_effect = ValueError(error_message)

        start_task_tool.run(id=1)

        mock_task_list.start_task.assert_called_once_with(id=1)
