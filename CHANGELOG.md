# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed

- Updated dependencies: anthropic (0.73.0 → 0.74.1), numpy (2.3.4 → 2.3.5), openai (2.8.0 → 2.8.1)

## [0.9.0] - 2025-11-13

### Added

- Added `LLMBroker.generate_stream()` method for streaming responses with full tool calling support
- Added `OpenAIGateway.complete_stream()` with intelligent tool argument accumulation and parsing
- Added streaming support for both Ollama and OpenAI gateways with recursive tool execution
- Added comprehensive streaming documentation at `docs/streaming.md`
- Added streaming example in main documentation (`docs/index.md`)
- Added security scanning with bandit (>=1.7.0) and pip-audit (>=2.0.0) to CI/CD pipeline
- Added JSON artifact generation for security scan results (bandit-report.json, pip-audit-report.json)

### Changed

- Enhanced `OllamaGateway.complete_stream()` to enable tool support (previously disabled)
- Updated `StreamingResponse` model to support both content chunks and tool calls
- Improved tool call ID preservation for proper message formatting in recursive calls
- Updated PARITY.md with comprehensive streaming capability documentation
- Enhanced CI/CD pipeline documentation with security scanning details

### Fixed

- Fixed streaming to properly yield content before tool calls (when LLM generates it)
- Fixed tool call ID propagation in streaming mode for OpenAI compatibility
- Fixed incremental tool argument streaming for OpenAI (arguments arrive in chunks)

## [0.8.4] - 2025-11-05

### Changed

- Adjusted OpenAIGateway to draw in OPENAI_API_KEY and OPENAI_API_ENDPOINT environment variables when no key or endpoint explicitly provided

## [0.8.3] - 2025-10-11

### Changed

- Enhanced API documentation with improved structure and new mermaid diagrams
- Added Layer 1 architecture diagram showing relationships between key classes
- Restructured Level 2 documentation to separate Simple Agents and Event-Driven Agents
- Improved async capabilities documentation with detailed sections on computation units and event-driven architecture
- Updated index documentation with practical code examples and sequence diagrams for common usage patterns
- Added mermaid diagrams illustrating simple one-shot completion, chat sessions, and asynchronous multi-agent systems

## [0.8.2] - 2025-01-25

### Fixed

- Changed ChatSession default temperature from 0.7 to 1.0 to ensure consistent behavior with OpenAI reasoning models that require temperature of 1.0

## [0.8.1] - 2025-09-28

### Fixed

- Fixed temperature parameter restrictions for OpenAI reasoning models that only support specific temperature values
- Fixed GPT-5 series models to automatically adjust unsupported temperature values (e.g., 0.1) to default (1.0) with warning
- Fixed o1 and o4 series models to automatically adjust unsupported temperature values to default (1.0) with warning
- Fixed o3 series models to automatically remove temperature parameter entirely (not supported) with warning
- Enhanced OpenAI model registry with comprehensive temperature restriction support for all reasoning model series
- Added automatic parameter adaptation that prevents BadRequestError exceptions for temperature restrictions
- Added comprehensive test coverage for temperature handling across all OpenAI reasoning models

## [0.8.0] - 2025-09-28

### Added

- Added comprehensive OpenAI model registry system with automatic model categorization and capabilities detection
- Added support for GPT-5 model series (gpt-5, gpt-5-mini, gpt-5-nano, etc.) as reasoning models
- Added support for GPT-4.1 model series as chat models
- Added automatic parameter adaptation system that converts `max_tokens` to `max_completion_tokens` for reasoning models
- Added enhanced logging for parameter conversions and model validation
- Added fetch_openai_models.py utility script for retrieving and categorizing current OpenAI models
- Added comprehensive test coverage for all GPT-5 model variants

### Changed

- Enhanced OpenAI gateway with registry-based parameter adaptation for backward compatibility
- Improved model categorization logic to distinguish between reasoning models (o1, o3, o4, gpt-5 series) and chat models (gpt-4, gpt-4.1, gpt-3.5 series)
- Updated model registry with 74+ current OpenAI models including latest GPT-5 and GPT-4.1 variants

### Fixed

- Fixed "Unsupported parameter: 'max_tokens' is not supported with this model" errors for all current OpenAI reasoning models
- Fixed parameter compatibility issues between different OpenAI model types
- Ensured proper handling of tools removal for models that don't support function calling

## [0.7.4] - 2024-12-20

### Added

- Added model characterization functionality to OpenAI gateway to distinguish between reasoning models (o1-mini, o1-preview, etc.) and chat models (gpt-4o, gpt-4o-mini, etc.)
- Added automatic parameter adaptation for reasoning models, converting `max_tokens` to `max_completion_tokens` as required by OpenAI's reasoning models

### Fixed

- Fixed parameter compatibility issues with OpenAI reasoning models by automatically adapting token limit parameters based on model type

## [0.7.3] - 2025-06-25

### Added

- Added max_tokens parameter to LLM gateways and LLMBroker for controlling the maximum number of tokens generated in responses

## [0.7.2] - 2025-06-22

### Added

- Added llms.txt support for easier LLM configuration
- Added extensive tests for `FilesystemGateway`, `FileManager`, and tools in `file_manager_spec.py`
- Introduced `IterativeProblemSolverTool` example to illustrate multi-level problem solving

### Changed

- Merged CI/CD pipeline to a single multistage workflow
- Refactored: Renamed `TestEvent` and `TestResponseEvent` to `SampleEvent` and `SampleResponseEvent`
- Replaced deprecated `dict()` with `model_dump()` in tracer-related methods for better compatibility
- Updated pytest configuration to streamline test discovery

### Fixed

- Fixed test failures by preventing module-level Ollama connection
- Removed circular import issues
- Removed unnecessary backward compatibility imports from tools __init__.py
- Maintained backward compatibility for bundled tools

## [0.7.1] - 2025-05-21

### Fixed

- Fixed image type handling in OpenAI adapter to ensure 'jpg' is properly converted to 'jpeg' when sending to OpenAI API

## [0.7.0] - 2025-05-20

### Added

- Added asynchronous capabilities with AsyncDispatcher for event processing
- Added BaseAsyncAgent class for creating asynchronous agents
- Added AsyncAggregatorAgent for combining events from multiple sources asynchronously
- Added BaseAsyncLLMAgent and BaseAsyncLLMAgentWithMemory for asynchronous LLM interactions
- Added async_dispatcher_example.py and async_llm_example.py to demonstrate async functionality
- Added documentation for async capabilities

### Changed

- Updated API documentation to include async functionality
- Improved event handling with correlation_id tracking across async operations

## [0.6.2] - 2025-05-17

### Added

- Added optional base_url parameter to OpenAIGateway to support custom API endpoints

## [0.6.1] - 2025-05-16

### Added

- Added correlation_id to tracer events for tracking cause and effect
- Added printable_summary method to tracer events for better object-oriented formatting
- Made the tracer event store observable

### Changed

- Renamed terminology from "Problem" to "Goal" to make things feel more universal
- Renamed instance properties to 'tracer' and removed setter methods
- Updated tracer_demo.py to use real ChatSession instead of synthetic events
- Implemented NullTracer pattern and improved tracer_demo example

## [0.6.0] - 2025-05-14

### Added

- Added observability via the TracerSystem, which provides a recorded trace of chat, llm, and tool interactions
  throughout a session.

## [0.5.7] - 2025-05-13

### Fixed

- Serialization bug in tool call results

## [0.5.6] - 2025-05-13

### Added

- Added comprehensive unit tests for task management tools
- New function to wrap tool .run() function, for MCP compatibility

## [0.5.5] - 2025-05-12

### Added

- Added EphemeralTaskList and accompanying LLM tools
- Added TellUserTool for displaying messages to the user without expecting a response

## [0.5.4] - 2025-04-30

### Fixed

- Added chunking functionality to OllamaGateway's calculate_embeddings method to handle oversized text inputs

### Added

- ability to set system prompt in the SimpleRecursiveAgent and IterativeProblemSolver
- added numpy to the dependency list, used by vector averaging function for chunking embeddings

## [0.5.3] - 2025-04-25

### Fixed

- Bug in MessageBuilder where initial prompt content was not being added to the message

## [0.5.2] - 2025-04-18

### Added

- Added ability to use a file reference as a template value in MessageBuilder
- Added documentation example for using file references as template values in MessageBuilder

## [0.5.1] - 2025-04-16

### Added

- Added load_content method to MessageBuilder to load content directly from a file
- Added template substitution functionality to load_content method in MessageBuilder

### Fixed

- Strip leading and trailing whitespace from file content in message composers

## [0.5.0] - 2025-04-14

### Added

- Added MessageBuilder class for constructing LLM messages with text content, images, and files
- Added FileTypeSensor for detecting file types added to LLMMessages

### Changed

- Minor version update for improved stability and performance

### Fixed

- Refactored docstrings to use consistent 'Parameters' and 'Returns' sections in file_gateway and message_composers

## [0.4.2] - 2025-03-27

### Changed

- Modified OllamaGateway and OpenAIGateway to return alphabetically sorted lists of available models

### Fixed

- Added missing docstring for OpenAIGateway's get_available_models method

## [0.4.1] - 2025-03-25

### Added

- Added stubbed calculate_embeddings method to LLMGateway base class for standardized interface
- Added return type annotations to calculate_embeddings methods in OllamaGateway and OpenAIGateway

### Fixed

- Added missing documentation for embeddings functionality in API Layer 1 guide

## [0.4.0] - 2025-03-23

### Added

- Added experimental model metadata classes for enhanced model registration and discovery
- Added embeddings functionality to OllamaGateway and OpenAIGateway
- Added support for image analysis in LLM gateways
- Added example demonstrating the use of embeddings functionality

### Deprecated

- Deprecated standalone EmbeddingsGateway class in favor of gateway-specific implementations

## [0.3.0] - 2025-03-17

### Added

- Added SimpleRecursiveAgent for enhanced problem-solving capabilities
- Added image analysis support in LLM gateways
- Added "Getting Started with Mojentic API Layer 1" guide
- Added support for image file paths in OllamaGateway's complete and complete_stream methods

### Changed

- Refactored IterativeProblemSolver to remove user_request parameter for improved clarity
- Refactored IterativeProblemSolver and SimpleRecursiveAgent for improved flexibility
- Updated navigation in documentation

### Fixed

- Fixed structured output for OpenAI
- Fixed documentation links

## [0.2.6] - 2025-03-09

### Added

- Development guidelines documentation
- Release process documentation
- Project structure documentation

### Changed

- Enhanced documentation with best practices
- Improved testing guidelines

## [0.2.5] - 2025-02-17

### Added

- Enhanced agent capabilities
- Improved documentation

## [0.2.4] - 2025-02-16

### Added

- Additional LLM tools
- Extended examples

## [0.2.3] - 2025-02-13

### Fixed

- Bug fixes and stability improvements

## [0.2.2] - 2025-02-05

### Added

- New agent features
- Additional documentation

## [0.2.1] - 2025-02-05

### Fixed

- Minor bug fixes
- Documentation updates

## [0.2.0] - 2025-02-04

### Added

- Advanced LLM integration features
- Enhanced context management
- Improved agent framework

## [0.1.0] - 2025-01-26

### Added

- Initial project structure
- Basic LLM integration with support for ollama/openai
- Agent framework foundation
- Context and shared memory implementation
- Development guidelines and documentation
