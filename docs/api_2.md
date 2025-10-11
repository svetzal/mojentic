# Level 2 - Elemental Agents and Events

This layer is about building Agents and the protocol by which a system of Agents can accomplish work.

> This layer is in flux! It will change frequently right now.

At this layer we currently have:

- [AsyncDispatcher](api_2.md#mojentic.async_dispatcher.AsyncDispatcher): A dispatcher that manages asynchronous execution of tasks, allowing agents to run operations concurrently.

- [IterativeProblemSolver](api_2.md#mojentic.agents.IterativeProblemSolver): An agent that solves problems iteratively by applying a Local Language Model (LLM) to a problem until a solution is found or a maximum number of iterations is reached.

- [SimpleRecursiveAgent](api_2.md#mojentic.agents.SimpleRecursiveAgent): An agent that solves problems recursively by applying an LLM to a problem until a solution is found or a maximum number of iterations is reached.

## Building Blocks

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

:::: mojentic.async_dispatcher.AsyncDispatcher
    options:
        show_root_heading: true
        merge_init_into_class: false
        group_by_category: false
