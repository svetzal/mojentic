# Mojentic Python — Project Charter

## Purpose

Mojentic is a Python framework for interacting with Large Language Models through a unified, provider-agnostic interface. It serves as the reference implementation for the Mojentic family of libraries (with ports in Elixir, Rust, and TypeScript), providing both direct LLM interaction and an emerging event-driven agent system.

## Goals

- Provide a simple, consistent API for text generation, structured output, and tool use across LLM providers (OpenAI, Ollama, Anthropic)
- Handle provider-specific quirks (parameter restrictions, message formatting) transparently so callers do not need to
- Support structured output generation via Pydantic models without requiring callers to manage JSON parsing
- Enable multi-agent coordination through an event dispatcher and router architecture
- Serve as the canonical reference for feature parity across all Mojentic language ports
- Provide observability into LLM calls and agent interactions through the TracerSystem

## Non-Goals

- Being a full application framework — Mojentic is a library, not an opinionated app scaffold
- Abstracting away model selection or cost management — callers choose their own models and providers
- Providing hosted infrastructure or managed services
- Replacing prompt engineering — Mojentic handles transport and structure, not prompt design

## Target Users

Python developers building applications that use LLMs, who want a clean abstraction over multiple providers without vendor lock-in. Also serves contributors maintaining the other Mojentic language ports who need a reference for expected behavior.
