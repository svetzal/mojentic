# Layer 1 - LLM Abstraction

This layer is about abstracting the function of an LLM, so that you can think about prompting and output and tool use in
a way that does not tie you to a specific LLM, its calling conventions, and the quirks of its specific library.

At this layer we have:

- [LLMBroker](api_1.md#mojentic.llm.LLMBroker): This is the main entrypoint to the layer. It leverages an LLM specific
  Gateway, and is the primary interface for interacting with the LLM on the other side. The LLMBroker correctly handles
  text generation, structured output, and tool use.

- [ChatSession](api_1.md#mojentic.llm.ChatSession): This is a simple class that wraps the LLMBroker and provides a
  conversational interface to the LLM with context size management. It is a good starting point for building a chatbot.

- [OllamaGateway](api_1.md#mojentic.llm.OllamaGateway), [OpenAIGateway](api_1.md#mojentic.llm.OpenAIGateway): These are
  out-of-the-box adapters that will interact with models available through
  Ollama and OpenAI.

- [LLMGateway](api_1.md#mojentic.llm.LLMGateway): This is the abstract class that all LLM adapters must inherit from. It
  provides a common interface and isolation point for interacting with LLMs.

## Building Blocks

::: mojentic.llm.LLMBroker
    options:
        show_root_heading: true
        merge_init_into_class: false
        group_by_category: false

::: mojentic.llm.ChatSession
    options:
        show_root_heading: true
        merge_init_into_class: false
        group_by_category: false

::: mojentic.llm.gateways.LLMGateway
    options:
        show_root_heading: true
        merge_init_into_class: false
        group_by_category: false

::: mojentic.llm.gateways.OllamaGateway
    options:
        show_root_heading: true
        merge_init_into_class: false
        group_by_category: false

::: mojentic.llm.gateways.OpenAIGateway
    options:
        show_root_heading: true
        merge_init_into_class: false
        group_by_category: false

::: mojentic.llm.gateways.models.LLMMessage
    options:
        show_root_heading: true
        merge_init_into_class: false
        group_by_category: false

::: mojentic.llm.gateways.models.LLMToolCall
    options:
        show_root_heading: true
        merge_init_into_class: false
        group_by_category: false

::: mojentic.llm.gateways.models.LLMGatewayResponse
    options:
        show_root_heading: true
        merge_init_into_class: false
        group_by_category: false