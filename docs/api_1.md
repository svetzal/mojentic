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

## Working with Images

Mojentic supports sending images to LLMs through the `image_paths` parameter in the `LLMMessage` class. This allows you to perform image analysis, OCR, and other vision-based tasks.

### Usage Example

```python
from mojentic.llm.gateways import OllamaGateway
from mojentic.llm.gateways.models import LLMMessage
from pathlib import Path

# Initialize the gateway
llmg = OllamaGateway()

# Send a message with an image
response = llmg.complete(
    model="gemma3",  # Use an image-capable model
    messages=[
        LLMMessage(
            content="Describe what you see in this image.",
            image_paths=[
                str(Path.cwd() / "images" / "example.jpg")
            ]
        )
    ],
)

print(response)
```

### Important Notes

- **Image-Capable Models**: You must use an image-capable model to process images. Not all models support image analysis.
  - For Ollama: Models like "gemma3", "llava", and "bakllava" support image analysis
  - For OpenAI: Models like "gpt-4-vision-preview" and "gpt-4o" support image analysis

- **Image Formats**: Supported image formats include JPEG, PNG, GIF, and WebP.

- **Implementation Details**:
  - For Ollama: Images are passed directly as file paths
  - For OpenAI: Images are base64-encoded and included in the message content

- **Performance Considerations**: Image analysis may require more tokens and processing time than text-only requests.

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
