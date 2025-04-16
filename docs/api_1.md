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

- [MessageBuilder](message_composers): This is a utility class for constructing messages
  with text, images, and file contents using a fluent interface.

## Working with Embeddings

Mojentic provides embeddings functionality through the `calculate_embeddings` method in both the `OllamaGateway` and `OpenAIGateway` classes. Embeddings are vector representations of text that capture semantic meaning, making them useful for similarity comparisons, clustering, and other NLP tasks.

### Usage Example

```python
from mojentic.llm.gateways import OllamaGateway, OpenAIGateway

# Initialize the gateways
ollama_gateway = OllamaGateway()
openai_gateway = OpenAIGateway(api_key="your-api-key")

# Calculate embeddings using Ollama
text = "This is a sample text for embeddings."
ollama_embeddings = ollama_gateway.calculate_embeddings(
    text=text,
    model="mxbai-embed-large"  # Default model for Ollama
)

# Calculate embeddings using OpenAI
openai_embeddings = openai_gateway.calculate_embeddings(
    text=text,
    model="text-embedding-3-large"  # Default model for OpenAI
)

# Use the embeddings for similarity comparison, clustering, etc.
print(f"Ollama embeddings dimension: {len(ollama_embeddings)}")
print(f"OpenAI embeddings dimension: {len(openai_embeddings)}")
```

### Important Notes

- **Available Models**:
  - For Ollama: Models like "mxbai-embed-large" (default), "nomic-embed-text" are commonly used
  - For OpenAI: Models like "text-embedding-3-large" (default), "text-embedding-3-small", "text-embedding-ada-002" are available

- **Embedding Dimensions**:
  - Different models produce embeddings with different dimensions
  - Ollama's "mxbai-embed-large" typically produces 1024-dimensional embeddings
  - OpenAI's "text-embedding-3-large" typically produces 3072-dimensional embeddings

- **Performance Considerations**:
  - Embedding generation is generally faster and less resource-intensive than text generation
  - Local embedding models (via Ollama) may be more cost-effective for high-volume applications

## Working with Images

Mojentic supports sending images to LLMs using the `MessageBuilder` class. This allows you to perform image analysis, OCR, and other vision-based tasks with a clean, fluent interface.

### Usage Example

```python
from mojentic.llm import LLMBroker
from mojentic.llm.message_composers import MessageBuilder
from pathlib import Path

# Initialize the LLM broker
llm = LLMBroker(model="gemma3:27b")  # Use an image-capable model

# Build a message with an image
message = MessageBuilder("Describe what you see in this image.")
    .add_image(Path.cwd() / "images" / "example.jpg")
    .build()

# Generate a response
result = llm.generate(messages=[message])

print(result)
```

### Important Notes

- **Image-Capable Models**: You must use an image-capable model to process images. Not all models support image analysis.
  - For Ollama: Models like "gemma3", "llava", and "bakllava" support image analysis
  - For OpenAI: Models like "gpt-4-vision-preview" and "gpt-4o" support image analysis

- **Image Formats**: Supported image formats include JPEG, PNG, GIF, and WebP.

- **Implementation Details**:
  - The `MessageBuilder` handles the appropriate encoding of images for different LLM providers
  - For Ollama: Images are passed as file paths (handled internally by MessageBuilder)
  - For OpenAI: Images are base64-encoded and included in the message content (handled internally by MessageBuilder)

- **Performance Considerations**: Image analysis may require more tokens and processing time than text-only requests.


## Building Blocks

::: mojentic.llm.MessageBuilder
    options:
        show_root_heading: true
        merge_init_into_class: false
        group_by_category: false

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
