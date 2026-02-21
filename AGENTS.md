# Mojentic Python — Project Guidance

**IMPORTANT**: Consult these guidelines early and often when working with this project.

## Project Overview

Mojentic is an agentic framework providing simple and flexible LLM interaction capabilities. This is the **reference implementation** for all language ports (Elixir, Rust, TypeScript). Changes here should be reflected in PARITY.md.

- **Tech stack**: Python 3.11+, Pydantic, structlog, pytest, MkDocs
- **Key dependencies**: pydantic (data validation), structlog (logging), ollama/openai (LLM integration)
- **Layer 1 API** (LLMBroker, LLMGateway, tool use) has stabilized
- **Layer 2** agentic capabilities are under heavy development

## Architecture

### Layer 1: LLM Integration (Stable)

**LLMBroker** (`mojentic.llm.llm_broker.LLMBroker`) is the primary interface:
- `generate()`: Text generation with optional tool calling
- `generate_object()`: Structured output using Pydantic models

**LLMGateway** (`mojentic.llm.gateways.llm_gateway.LLMGateway`) is the base abstraction for LLM providers:
- Implement `complete()` method for new providers
- Current implementations: OpenAIGateway, OllamaGateway, AnthropicGateway
- OpenAI gateway handles model-specific parameter limitations automatically (GPT-5, o1/o3/o4 series)

**Message Handling**:
- `LLMMessage` model defines message structure with role, content, tool_calls, image_paths
- Provider-specific adapters (OpenAIMessagesAdapter, OllamaMessagesAdapter, AnthropicMessagesAdapter) convert between universal LLMMessage format and provider APIs

### Layer 2: Agent System (Under Development)

**Event Dispatcher Pattern**:
- `Dispatcher` manages event-based communication between agents
- Routes events to agents via `Router` configuration
- Agents process events via `receive_event()` and emit new events

**Agent Hierarchy**:
- `BaseAgent`: Foundation for all agents
- `BaseLLMAgent`: Adds LLM capabilities, tools, and behavior configuration
- `BaseLLMAgentWithMemory`: Extends with `SharedWorkingMemory` integration
- `AsyncLLMAgent`: Asynchronous LLM processing

### Observability: TracerSystem

The `TracerSystem` (`mojentic.tracer.tracer_system.TracerSystem`) provides comprehensive observability:
- Records LLM calls, responses, tool calls, and agent interactions
- Events stored in `EventStore` with timestamp-based querying
- Correlation IDs link related events across the system
- Can be disabled or use `null_tracer` for zero overhead
- Pass tracer to LLMBroker, Dispatcher, and agents for complete visibility

**Integration Pattern**:
```python
from mojentic.tracer import TracerSystem

tracer = TracerSystem()
broker = LLMBroker(model="gpt-4o", gateway=OpenAIGateway(), tracer=tracer)
dispatcher = Dispatcher(router, tracer=tracer)
```

## Project Structure

```
docs/                  # Documentation files (MkDocs)
src/
├── mojentic/          # Main package
│   ├── agents/        # Agent implementations
│   ├── audit/         # Audit and logging functionality
│   ├── context/       # Shared memory and context
│   ├── llm/           # LLM integration
│   │   ├── gateways/  # LLM provider adapters
│   │   ├── registry/  # Model registration
│   │   └── tools/     # Utility tools
│   ├── utils/         # Utility functions and helpers
│   ├── dispatcher.py  # Event dispatching functionality
│   ├── event.py       # Event definitions
│   └── router.py      # Message routing
├── _examples/         # Usage examples
    ├── images/        # Example images for image analysis
    └── react/         # ReAct pattern examples
```

## Coding Standards

### Error Handling
- Use exceptions for error conditions
- Raise specific exception types, not generic `Exception`
- Document exceptions in docstrings with `Raises` section
- Use `try/except` for expected errors, let unexpected ones propagate
- Use context managers (`with`) for resource management

### Code Style
- Follow PEP 8 style guide
- Max line length: 127
- Max complexity: 10
- Use numpy-style docstrings for all public APIs
- Use type hints for all function signatures
- Use `flake8` for linting
- Favor declarative code over imperative code
- Favor list and dictionary comprehensions over for loops
- Use Pydantic models (not `@dataclass`) for data objects
- Use type hints: `List[str]`, `Dict[str, int]`, `Optional[int]`
- Use `set()` for membership testing on large collections

### Common Mistakes to Avoid
- Don't use mutable default arguments: `def func(items=[]):` — use `def func(items=None):` instead
- Don't use bare `except:` — always specify exception types
- Don't use `is` for value comparison — use `==` (except for `None`, `True`, `False`)
- Don't mutate function arguments unexpectedly
- Don't use `eval()` or `exec()` on untrusted input

## Testing

- Tests are co-located with implementation files (test file must be in the same folder)
- Tests are written as specifications in `*_spec.py` files
- Test discovery includes: `test_*.py`, `*_test.py`, `*_spec.py` in `src/`
- **Test naming**: Use `should_*` for test methods, `Describe*` for test classes
- Use pytest with `mocker` fixture for mocking — do not use `unittest` or `MagicMock` directly
- Use `@fixture` markers for pytest fixtures
- Break large fixtures into smaller, focused fixtures
- Do not write Given/When/Then or Act/Arrange/Assert comments
- Do not write docstrings on `should_` methods
- Separate test phases with a single blank line
- Do not write conditional statements in tests
- Each test must fail for only one clear reason
- **Mocking rule**: Only mock our own gateway classes. Do not mock other library internals or private functions/methods in our own code

## LLM Tool Development

- Model new tools after `mojentic.llm.tools.date_resolver.ResolveDateTool`
- All tools extend the `LLMTool` base class
- For LLM-based tools, take `LLMBroker` as a parameter in the tool's initializer
- Use `LLMBroker.generate_object()` for structured output — do not ask the LLM to generate JSON directly

## Quality Guidelines

### MANDATORY Pre-Commit Quality Gates

**STOP**: Before considering ANY work complete or committing code, run ALL quality checks:

```bash
uv run flake8 src && uv run pytest && uv run pip-audit
```

**Why this matters**: Examples and tests must pass. When examples fail, users cannot learn from them. `flake8` validates all Python files including examples.

**If any check fails**:
- STOP immediately
- Fix the root cause (don't suppress warnings)
- Re-run all checks
- Only proceed when all pass

## Security Guidelines

### Dependency Security
- Run `pip-audit` to check for known vulnerabilities
- Keep dependencies up to date, especially security patches
- Review security advisories regularly
- Use virtual environments to isolate dependencies

### Secure Coding
- Validate all inputs, especially from external sources
- Never use `eval()` or `exec()` on user input
- Use `secrets` module for cryptographic operations, not `random`
- Don't log sensitive data (API keys, passwords, tokens)
- Use environment variables for configuration, not hardcoded values

## Documentation

- Built with MkDocs + Material theme + mkdocstrings
- Supports mermaid.js diagrams in markdown
- Keep `mkdocs.yml` navigation tree synchronized with `docs/` folder
- Use blank lines around lists, headings, code blocks, and blockquotes
- Keep README.md synchronized with actual functionality

### API Documentation

API documentation uses mkdocstrings markers in markdown:

```
::: mojentic.llm.LLMBroker
    options:
        show_root_heading: true
        merge_init_into_class: false
        group_by_category: false
```

Always use the same `show_root_heading`, `merge_init_into_class`, and `group_by_category` options.

## Release Process

### Versioning
- Follow semantic versioning (semver): MAJOR.MINOR.PATCH
- Update version in `pyproject.toml`
- Update `CHANGELOG.md` with release notes
- Use `v` prefix for tags (e.g., `v1.0.0`) to match other Mojentic implementations

### Publishing a Release

**The release pipeline is fully automated.** When you create a GitHub release, the CI/CD workflow will:
1. Run all quality checks (lint, test, security audit)
2. Build and publish the package to PyPI (using trusted publishing)
3. Deploy documentation to GitHub Pages

#### Steps to Release

```bash
# 1. Update version in pyproject.toml (e.g., version = "1.1.0")

# 2. Update CHANGELOG.md
#    - Add new version section with date: ## [1.1.0] - YYYY-MM-DD
#    - Document all changes under appropriate headers (Added, Changed, Fixed, etc.)

# 3. Commit and push
git add pyproject.toml CHANGELOG.md
git commit -m "chore: prepare v1.1.0 release"
git push origin main

# 4. Create GitHub release (this triggers the publish)
gh release create v1.1.0 \
  --title "v1.1.0 - Release Title" \
  --notes "## What's New

- Feature 1
- Feature 2

See [CHANGELOG.md](CHANGELOG.md) for full details."
```

The pipeline uses PyPI trusted publishing — no API tokens needed in GitHub secrets.

### CI/CD Pipeline

The GitHub Actions workflow (`.github/workflows/build.yml`) runs:

| Trigger | Quality Checks | Docs Deploy | PyPI Publish |
|---------|---------------|-------------|--------------|
| Push to main | Yes | No | No |
| Pull request | Yes | No | No |
| Release published | Yes | Yes | Yes |

### Release Types

- **Major (x.0.0)**: Breaking API changes, removal of deprecated features. Provide migration guides.
- **Minor (0.x.0)**: New features (backward-compatible), deprecation notices, performance improvements.
- **Patch (0.0.x)**: Bug fixes, security updates, documentation corrections.

### Pre-Release Checklist

- [ ] All tests pass: `uv run pytest`
- [ ] Linting passes: `uv run flake8 src`
- [ ] Security audit clean: `uv run pip-audit`
- [ ] Docs build: `uv run mkdocs build`
- [ ] Version updated in `pyproject.toml`
- [ ] CHANGELOG.md updated
- [ ] Changes committed and pushed to main

## Branding

Mojentic is a Mojility product:
- Accent Green: #6bb660
- Dark Grey: #666767
- Use official Mojility logo in original colors and proportions

## Development Setup

This project uses **uv** for all Python environment and dependency management.

```bash
# Install uv if not present (macOS/Linux)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Sync all dependencies (runtime + dev group)
uv sync

# Run commands via uv — no manual venv activation needed
uv run pytest           # Run tests
uv run flake8 src       # Run linting
uv run pip-audit        # Security audit
uv run mkdocs serve     # Serve docs locally
```

## Useful Commands

```bash
# Testing
uv run pytest                                      # All tests with coverage
uv run pytest src/mojentic/llm/llm_broker_spec.py  # Single test file
uv run pytest -k test_name                         # Specific test by name

# Linting & Security
uv run flake8 src                    # Python linting
uv run bandit -c .bandit -r src      # Security scan (with config)
uv run pip-audit                     # Dependency vulnerability check

# Documentation
uv run mkdocs serve  # Serve docs locally at http://127.0.0.1:8000
uv run mkdocs build  # Build static site

# Before Committing
uv run flake8 src && uv run pytest && uv run pip-audit
```

## Examples

Example scripts are in `src/_examples/`. Common patterns:
- `simple_llm.py`: Basic LLM usage
- `chat_session.py`: Chat interactions
- `working_memory.py`: Context management

```python
from mojentic.llm import LLMBroker
from mojentic.agents import BaseLLMAgent
```
