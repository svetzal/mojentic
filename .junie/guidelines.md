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
3. Install pre-commit hooks (recommended):
   ```bash
   # Create a pre-commit hook that runs pytest
   cat > .git/hooks/pre-commit << 'EOL'
   #!/bin/sh

   # Run pytest
   echo "Running pytest..."
   python -m pytest

   # Store the exit code
   exit_code=$?

   # Exit with pytest's exit code
   exit $exit_code
   EOL

   # Make the hook executable
   chmod +x .git/hooks/pre-commit
   ```

## Testing Guidelines
- Tests are co-located with implementation files (test file must be in the same folder as the implementation)
- Run tests: `pytest`
- Linting: `flake8 src`
- Code style:
  - Max line length: 127
  - Max complexity: 10
  - Follow numpy docstring style

### Testing Best Practices
- Use pytest for testing, with mocker if you require mocking
- Do not use unittest or MagicMock directly, use it through the mocker wrapper
- Use @fixture markers for pytest fixtures
- Break up fixtures into smaller fixtures if they are too large
- Do not write Given/When/Then or Act/Arrange/Assert comments
- Separate test phases with a single blank line
- Do not write conditional statements in tests
- Each test must fail for only one clear reason
- "Don't Mock what you don't own" only write mocks for our own gateway classes, do not mock other library internals or
  even private functions or methods in our own code.

## Best Practices
1. Follow the existing project structure
2. Write tests for new functionality
3. Document using numpy-style docstrings
4. Keep code complexity low
5. Use type hints for all functions and methods
6. Co-locate tests with implementation
7. Favor declarative code styles over imperative code styles
8. Use pydantic (not @dataclass) for data objects with strong types
9. Favor list and dictionary comprehensions over for loops

## Mojentic Development
### LLM Tool Development
1. When writing a new LLM tool, model the implementation after `mojentic.llm.tools.date_resolver.ResolveDateTool`
2. For LLM-based tools, take the LLMBroker object as a parameter in the tool's initializer
3. Don't ask the LLM to generate JSON directly, use the `LLMBroker.generate_object()` method instead

## Documentation
- Built with MkDocs and Material theme
- API documentation uses mkdocstrings
- Supports mermaid.js diagrams in markdown files:
  ```mermaid
  graph LR
      A[Doc] --> B[Feature]
  ```
- Build docs locally: `mkdocs serve`
- Build for production: `mkdocs build`

## Release Process
1. Update CHANGELOG.md:
   - All notable changes should be documented under the [Unreleased] section
   - Group changes into categories:
     - Added: New features
     - Changed: Changes in existing functionality
     - Deprecated: Soon-to-be removed features
     - Removed: Removed features
     - Fixed: Bug fixes
     - Security: Security vulnerability fixes
   - Each entry should be clear and understandable to end-users
   - Reference relevant issue/PR numbers where applicable

2. Creating a Release:
   - Ensure `pyproject.toml` has the next release version
   - Ensure all changes are documented in CHANGELOG.md
     - Move [Unreleased] changes to the new version section (e.g., [1.0.0])
   - Follow semantic versioning:
     - MAJOR version for incompatible API changes
     - MINOR version for backward-compatible new functionality
     - PATCH version for backward-compatible bug fixes

3. Best Practices:
   - Keep entries concise but descriptive
   - Write from the user's perspective
   - Include migration instructions for breaking changes
   - Document API changes thoroughly
   - Update documentation to reflect the changes

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
