# Task Management

The `mojentic.llm.tools.TaskManager` tool allows agents to manage ephemeral tasks during their execution. This is useful for breaking down complex goals into smaller, trackable steps.

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
