# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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
