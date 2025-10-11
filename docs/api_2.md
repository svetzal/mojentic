# Level 2 - Elemental Agents and Events

This layer is about building Agents and the protocol by which a system of Agents can accomplish work.

> This layer is in flux! It will change frequently right now.

## Simple Agents

Simple agents provide straightforward, synchronous approaches to problem-solving using LLMs.

- [IterativeProblemSolver](#mojentic.agents.IterativeProblemSolver): An agent that solves problems iteratively by applying a Local Language Model (LLM) to a problem until a solution is found or a maximum number of iterations is reached.

- [SimpleRecursiveAgent](#mojentic.agents.SimpleRecursiveAgent): An agent that solves problems recursively by applying an LLM to a problem until a solution is found or a maximum number of iterations is reached.

### API Reference

::: mojentic.agents.IterativeProblemSolver
    options:
        show_root_heading: true
        merge_init_into_class: false
        group_by_category: false

::: mojentic.agents.SimpleRecursiveAgent
    options:
        show_root_heading: true
        merge_init_into_class: false
        group_by_category: false

## Event Driven Agents

Event-driven agents provide asynchronous, event-based architectures for building complex agent systems that can process multiple events concurrently.

- [BaseAsyncAgent](#mojentic.agents.base_async_agent.BaseAsyncAgent): The foundation for all asynchronous agents, providing the core event processing interface.

- [BaseAsyncLLMAgent](#mojentic.agents.async_llm_agent.BaseAsyncLLMAgent): An asynchronous agent that integrates LLM capabilities for generating responses asynchronously.

- [AsyncAggregatorAgent](#mojentic.agents.async_aggregator_agent.AsyncAggregatorAgent): A specialized agent that collects and aggregates multiple events by correlation ID before processing them together.

- [AsyncDispatcher](#mojentic.async_dispatcher.AsyncDispatcher): The core dispatcher that manages asynchronous execution of tasks and coordinates event routing between agents.

### API Reference

::: mojentic.agents.base_async_agent.BaseAsyncAgent
    options:
        show_root_heading: true
        merge_init_into_class: false
        group_by_category: false

::: mojentic.agents.async_llm_agent.BaseAsyncLLMAgent
    options:
        show_root_heading: true
        merge_init_into_class: false
        group_by_category: false

::: mojentic.agents.async_aggregator_agent.AsyncAggregatorAgent
    options:
        show_root_heading: true
        merge_init_into_class: false
        group_by_category: false

::: mojentic.async_dispatcher.AsyncDispatcher
    options:
        show_root_heading: true
        merge_init_into_class: false
        group_by_category: false
