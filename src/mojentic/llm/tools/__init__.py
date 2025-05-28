"""
Mojentic LLM tools module for extending LLM capabilities.
"""

# Base tool class
from .llm_tool import LLMTool
from .tool_wrapper import ToolWrapper

# Common tools
from .ask_user_tool import AskUserTool
from .current_datetime import CurrentDateTimeTool
from .date_resolver import ResolveDateTool
from .organic_web_search import OrganicWebSearchTool
from .tell_user_tool import TellUserTool

# Import tool modules
from . import file_manager
from . import ephemeral_task_manager

# Re-export file_manager tools for backward compatibility
from .file_manager import FileManager, ReadFileTool, WriteFileTool, ListFilesTool

# Re-export ephemeral_task_manager tools for backward compatibility
from .ephemeral_task_manager import (
    EphemeralTaskList,
    Task,
    AppendTaskTool,
    PrependTaskTool,
    InsertTaskAfterTool,
    StartTaskTool,
    CompleteTaskTool,
    ListTasksTool,
    ClearTasksTool
)
