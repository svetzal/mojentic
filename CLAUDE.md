# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Mojentic is an agentic framework providing simple and flexible LLM interaction capabilities. Layer 1 API (LLMBroker, LLMGateway, tool use) has stabilized, while Layer 2 agentic capabilities are under heavy development and will likely change significantly.

## Development Commands

### Testing
```bash
# Run all tests (spec-style output with coverage)
pytest

# Run a specific test file
pytest src/mojentic/llm/llm_broker_spec.py

# Run linting
flake8 src
```

### Documentation
```bash
# Build and serve docs locally
mkdocs serve

# Build for production
mkdocs build
```

### Installation
```bash
# Install for development
pip install -e ".[dev]"
```

## Architecture

### Layer 1: LLM Integration (Stable)

**LLMBroker** (`mojentic.llm.llm_broker.LLMBroker`) is the primary interface for LLM interactions:
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

**Tools**:
- All tools extend `LLMTool` base class
- Model new tools after `mojentic.llm.tools.date_resolver.ResolveDateTool`
- LLM-based tools take `LLMBroker` in their initializer
- Use `LLMBroker.generate_object()` instead of asking LLM to generate JSON directly

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

## Code Style

- **Testing**: Co-locate test files (`*_spec.py`) with implementation
- **Test naming**: Use `should_*` for test methods, `Describe*` for test classes
- **Test style**: No Given/When/Then comments, no docstrings on test methods, separate phases with single blank line
- **Mocking**: Use pytest's `mocker` fixture, not unittest.mock directly. Only mock our own gateways, not library internals
- **Data models**: Use Pydantic (not @dataclass) for all data objects
- **Type hints**: Required for all functions and methods
- **Docstrings**: Use numpy-style for all public APIs
- **Code complexity**: Max line length 127, max complexity 10
- **Style preference**: Favor declarative over imperative, use comprehensions over for loops

## Testing Guidelines

- Run pytest before committing (pre-commit hook recommended)
- Each test must fail for only one clear reason
- Break large fixtures into smaller, focused fixtures
- No conditional statements in tests
- Test discovery: `test_*.py`, `*_test.py`, `*_spec.py` in `src/`

## Documentation

- Built with MkDocs + Material theme + mkdocstrings
- Mermaid.js diagrams supported in markdown
- Keep `mkdocs.yml` navigation tree synchronized with `docs/` folder
- Use blank lines around lists, headings, code blocks, and blockquotes
- API documentation uses mkdocstrings with markers like `::: mojentic.llm.LLMBroker`
- Standard options: `show_root_heading: true`, `merge_init_into_class: false`, `group_by_category: false`

## Branding

Mojentic is a Mojility product:
- Accent Green: #6bb660
- Dark Grey: #666767
- Use official Mojility logo in original colors and proportions
