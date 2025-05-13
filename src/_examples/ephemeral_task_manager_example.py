"""
Example script demonstrating the usage of the ephemeral task manager tools.
"""
import logging
import os

from mojentic.llm.gateways import OpenAIGateway

logging.basicConfig(
    level=logging.WARN
)

from mojentic.llm import LLMBroker
from mojentic.llm.gateways.models import LLMMessage
from mojentic.llm.tools.ephemeral_task_manager import (
    EphemeralTaskList,
    AppendTaskTool,
    PrependTaskTool,
    InsertTaskAfterTool,
    StartTaskTool,
    CompleteTaskTool,
    ListTasksTool,
    ClearTasksTool
)
from mojentic.llm.tools.tell_user_tool import TellUserTool

# llm = LLMBroker(model="qwen3:30b-a3b-q4_K_M")
# llm = LLMBroker(model="qwen3:32b")
llm = LLMBroker(model="qwen2.5:7b")
# llm = LLMBroker(model="qwen2.5:72b")
# llm = LLMBroker(model="o4-mini", gateway=OpenAIGateway(os.environ["OPENAI_API_KEY"]))
message = LLMMessage(
    content="I want you to count from 1 to 10. Break that request down into individual tasks, track them using available tools, and perform them one by one until you're finished. Interrupt me to tell the user as you complete every task.")
task_list = EphemeralTaskList()
tools = [
    AppendTaskTool(task_list),
    PrependTaskTool(task_list),
    InsertTaskAfterTool(task_list),
    StartTaskTool(task_list),
    CompleteTaskTool(task_list),
    ListTasksTool(task_list),
    ClearTasksTool(task_list),
    TellUserTool(),
]

result = llm.generate(messages=[message], tools=tools, temperature=0.0)
print(result)
print(task_list.list_tasks())