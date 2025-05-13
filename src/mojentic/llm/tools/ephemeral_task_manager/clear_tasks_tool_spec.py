import pytest
from unittest.mock import Mock

from mojentic.llm.tools.ephemeral_task_manager.clear_tasks_tool import ClearTasksTool
from mojentic.llm.tools.ephemeral_task_manager.ephemeral_task_list import EphemeralTaskList


@pytest.fixture
def mock_task_list():
    mock = Mock(spec=EphemeralTaskList)
    return mock


@pytest.fixture
def clear_tasks_tool(mock_task_list):
    return ClearTasksTool(task_list=mock_task_list)


class DescribeClearTasksTool:
    def should_call_clear_tasks(self, clear_tasks_tool, mock_task_list):
        mock_task_list.clear_tasks.return_value = 3  # Simulate clearing 3 tasks

        clear_tasks_tool.run()

        mock_task_list.clear_tasks.assert_called_once()

    def should_handle_empty_list(self, clear_tasks_tool, mock_task_list):
        mock_task_list.clear_tasks.return_value = 0  # Simulate clearing 0 tasks

        clear_tasks_tool.run()

        mock_task_list.clear_tasks.assert_called_once()
