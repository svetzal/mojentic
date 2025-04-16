# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.5.0] - 2025-04-01

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
