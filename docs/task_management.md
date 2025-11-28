# Example: Task Management

The `mojentic.llm.tools.TaskManager` is an example of how to build stateful tools that allow agents to manage ephemeral tasks. This reference implementation shows how to maintain state across tool calls.

## Features

- **Create Tasks**: Add new tasks to the list
- **List Tasks**: View all current tasks and their status
- **Complete Tasks**: Mark tasks as done
- **Prioritize**: Agents can determine the order of execution

## Usage

```python
from mojentic.llm import LLMBroker, LLMMessage
from mojentic.llm.gateways import OllamaGateway
from mojentic.llm.tools import TaskManager

# Initialize broker
broker = LLMBroker(model="qwen3:32b", gateway=OllamaGateway())

# Register the tool
tools = [TaskManager()]

# The agent can now manage its own tasks
messages = [
    LLMMessage(role="system", content="You are a helpful assistant. Use the task manager to track your work."),
    LLMMessage(content="Plan a party for 10 people.")
]

response = broker.generate(messages, tools=tools)
print(response)
```

## Integration with Agents

The Task Manager is particularly powerful when combined with the `IterativeProblemSolver` agent, allowing it to maintain state across multiple reasoning steps.
