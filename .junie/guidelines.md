# Mojentic Development Guidelines

## Project Overview
Mojentic is an agentic framework that provides a simple and flexible way to assemble teams of agents to solve complex problems. It supports integration with various LLM providers and includes tools for task automation.

## Tech Stack
- Python 3.11+
- Key Dependencies:
  - pydantic: Data validation
  - structlog: Logging
  - ollama/openai: LLM integration
  - pytest: Testing
  - MkDocs: Documentation

## Project Structure
```
src/
├── mojentic/           # Main package
│   ├── agents/        # Agent implementations
│   ├── context/       # Shared memory and context
│   ├── llm/          # LLM integration
│   │   ├── gateways/ # LLM provider adapters
│   │   ├── registry/ # Model registration
│   │   └── tools/    # Utility tools
├── _examples/         # Usage examples
```

## Development Setup
1. Install Python 3.11 or higher
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   pip install -r dev-requirements.txt
   ```
3. Install pre-commit hooks (recommended)

## Testing Guidelines
- Tests are co-located with implementation files
- Run tests: `pytest`
- Linting: `flake8 src`
- Code style:
  - Max line length: 127
  - Max complexity: 10
  - Follow numpy docstring style

## Best Practices
1. Follow the existing project structure
2. Write tests for new functionality
3. Document using numpy-style docstrings
4. Keep code complexity low
5. Use type hints
6. Co-locate tests with implementation

## Running Scripts
1. Example scripts are in `src/_examples/`
2. Basic usage:
   ```python
   from mojentic.llm import LLMBroker
   from mojentic.agents import BaseLLMAgent
   ```
3. See example files for common patterns:
   - simple_llm.py: Basic LLM usage
   - chat_session.py: Chat interactions
   - working_memory.py: Context management