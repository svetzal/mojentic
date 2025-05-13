from unittest.mock import Mock

import pytest

from mojentic.llm.tools.ephemeral_task_manager.complete_task_tool import CompleteTaskTool
from mojentic.llm.tools.ephemeral_task_manager.ephemeral_task_list import EphemeralTaskList, Task, TaskStatus


@pytest.fixture
def mock_task_list():
    mock = Mock(spec=EphemeralTaskList)
    return mock


@pytest.fixture
def complete_task_tool(mock_task_list):
    return CompleteTaskTool(task_list=mock_task_list)


class DescribeCompleteTaskTool:
    def should_call_complete_task_with_correct_id(self, complete_task_tool, mock_task_list):
        mock_task = Task(id=1, description="Test task", status=TaskStatus.COMPLETED)
        mock_task_list.complete_task.return_value = mock_task

        complete_task_tool.run(id=1)

        mock_task_list.complete_task.assert_called_once_with(id=1)

    def should_convert_string_id_to_int(self, complete_task_tool, mock_task_list):
        mock_task = Task(id=1, description="Test task", status=TaskStatus.COMPLETED)
        mock_task_list.complete_task.return_value = mock_task

        complete_task_tool.run(id="1")

        mock_task_list.complete_task.assert_called_once_with(id=1)

    def should_handle_error_when_complete_task_fails(self, complete_task_tool, mock_task_list):
        error_message = "Task '1' cannot be completed because it is not in IN_PROGRESS status"
        mock_task_list.complete_task.side_effect = ValueError(error_message)

        complete_task_tool.run(id=1)

        mock_task_list.complete_task.assert_called_once_with(id=1)
