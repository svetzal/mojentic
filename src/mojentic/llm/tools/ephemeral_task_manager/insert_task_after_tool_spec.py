from unittest.mock import Mock

import pytest

from mojentic.llm.tools.ephemeral_task_manager.ephemeral_task_list import EphemeralTaskList, Task, TaskStatus
from mojentic.llm.tools.ephemeral_task_manager.insert_task_after_tool import InsertTaskAfterTool


@pytest.fixture
def mock_task_list():
    mock = Mock(spec=EphemeralTaskList)
    return mock


@pytest.fixture
def insert_task_after_tool(mock_task_list):
    return InsertTaskAfterTool(task_list=mock_task_list)


class DescribeInsertTaskAfterTool:
    def should_call_insert_task_after_with_correct_parameters(self, insert_task_after_tool, mock_task_list):
        mock_task = Task(id=2, description="Test task", status=TaskStatus.PENDING)
        mock_task_list.insert_task_after.return_value = mock_task

        insert_task_after_tool.run(existing_task_id=1, description="Test task")

        mock_task_list.insert_task_after.assert_called_once_with(existing_task_id=1, description="Test task")

    def should_convert_string_task_id_to_int(self, insert_task_after_tool, mock_task_list):
        mock_task = Task(id=2, description="Test task", status=TaskStatus.PENDING)
        mock_task_list.insert_task_after.return_value = mock_task

        insert_task_after_tool.run(existing_task_id="1", description="Test task")

        mock_task_list.insert_task_after.assert_called_once_with(existing_task_id=1, description="Test task")

    def should_handle_error_when_insert_task_after_fails(self, insert_task_after_tool, mock_task_list):
        mock_task_list.insert_task_after.side_effect = ValueError("No task with ID '999' exists")

        insert_task_after_tool.run(existing_task_id=999, description="Test task")

        mock_task_list.insert_task_after.assert_called_once_with(existing_task_id=999, description="Test task")
