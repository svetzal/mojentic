# File Tools

Mojentic provides powerful tools for interacting with the file system, allowing agents to read, write, and manage files.

## Available Tools

### FileTool

The `mojentic.llm.tools.FileTool` provides basic file operations:

- `read_file`: Read content of a file
- `write_file`: Write content to a file
- `list_dir`: List directory contents
- `file_exists`: Check if a file exists

### CodingFileTool

The `mojentic.llm.tools.CodingFileTool` extends `FileTool` with features specifically for coding tasks:

- `apply_patch`: Apply a unified diff patch to a file
- `replace_text`: Replace specific text in a file
- `search_files`: Search for patterns in files

## Usage

```python
from mojentic.llm import LLMBroker, LLMMessage
from mojentic.llm.gateways import OllamaGateway
from mojentic.llm.tools import FileTool

# Initialize broker
broker = LLMBroker(model="qwen3:32b", gateway=OllamaGateway())

# Register tools
tools = [FileTool()]

# Ask the agent to perform file operations
messages = [
    LLMMessage(content="Create a file named 'hello.txt' with the content 'Hello, World!'")
]

response = broker.generate(messages, tools=tools)
print(response)
```

## Security

By default, file tools are restricted to the current working directory. You can configure allowed paths to restrict access further.
