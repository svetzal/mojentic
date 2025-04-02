# Image Analysis with LLMs in Mojentic

## Why Use Image Analysis with LLMs?

Modern Large Language Models (LLMs) have evolved beyond text processing to include multimodal capabilities, allowing them to analyze and understand images. This powerful feature enables you to:

- Extract information from visual content
- Generate descriptions of images
- Identify objects, text, and patterns in images
- Answer questions about visual content
- Combine visual and textual information for more comprehensive analysis

By integrating image analysis with LLMs, you can build applications that understand and process both textual and visual information, opening up a wide range of use cases that were previously difficult to implement.

## When to Apply This Approach

Use image analysis with LLMs when:
- You need to extract information from images or screenshots
- Your application needs to understand visual content
- You want to generate descriptions or captions for images
- You need to answer questions about visual content
- You're building applications that combine visual and textual data

Common applications include content moderation, document analysis, visual search, accessibility features, and multimodal chatbots.

## Getting Started

Let's walk through an example of using image analysis with Mojentic. We'll use a multimodal LLM to analyze an image and generate a description.

### Basic Implementation

Here's a simple example of analyzing an image with an LLM:

```python
from pathlib import Path
from mojentic.llm.gateways.models import LLMMessage
from mojentic.llm.llm_broker import LLMBroker

# Create an LLM broker with a multimodal model
# Note: For OpenAI, use "gpt-4o" or another vision-capable model
llm = LLMBroker(model="gemma3:27b")  # For Ollama, use a multimodal model

# Generate a response that includes image analysis
result = llm.generate(messages=[
    LLMMessage(
        content='What is in this image?',
        image_paths=[str(Path.cwd() / 'src' / '_examples' / 'images' / 'flash_rom.jpg')]
    )
])

print(result)
```

This code will generate a description of the image, identifying what's shown in the picture.

## Step-by-Step Explanation

Let's break down how this example works:

### 1. Import the necessary components

```python
from pathlib import Path
from mojentic.llm.gateways.models import LLMMessage
from mojentic.llm.llm_broker import LLMBroker
```

These imports provide:
- `Path`: A class for working with file paths in a cross-platform way
- `LLMMessage`: A class for creating messages to send to the LLM
- `LLMBroker`: The main interface for interacting with LLMs

### 2. Create an LLM broker with a multimodal model

```python
llm = LLMBroker(model="gemma3:27b")  # For Ollama, use a multimodal model
```

For image analysis, you need to use a model that supports multimodal inputs:
- For OpenAI, models like "gpt-4o" support vision
- For Ollama, models like "gemma3" or "llava" support vision

### 3. Create a message with an image

```python
message = LLMMessage(
    content='What is in this image?',
    image_paths=[str(Path.cwd() / 'src' / '_examples' / 'images' / 'flash_rom.jpg')]
)
```

The key difference for image analysis:
- We include the `image_paths` parameter in the `LLMMessage`
- This parameter takes a list of file paths to the images you want to analyze
- You can include multiple images in a single message

### 4. Generate a response that includes image analysis

```python
result = llm.generate(messages=[message])
```

The `generate` method works the same way as in previous examples, but now the LLM will:
1. Process the text prompt ("What is in this image?")
2. Load and analyze the image
3. Generate a response that incorporates its understanding of the image

### 5. Display the result

```python
print(result)
```

The result is a string containing the LLM's description or analysis of the image.

## Asking Specific Questions About Images

You can ask more specific questions about images to get targeted information:

```python
# Ask a specific question about the image
result = llm.generate(messages=[
    LLMMessage(
        content='Is there any text visible in this image? If so, what does it say?',
        image_paths=[str(Path.cwd() / 'src' / '_examples' / 'images' / 'screen_cap.png')]
    )
])

print(result)
```

## Using Multiple Images

You can include multiple images in a single message:

```python
# Compare multiple images
result = llm.generate(messages=[
    LLMMessage(
        content='Compare these two images and tell me the differences.',
        image_paths=[
            str(Path.cwd() / 'src' / '_examples' / 'images' / 'image1.jpg'),
            str(Path.cwd() / 'src' / '_examples' / 'images' / 'image2.jpg')
        ]
    )
])

print(result)
```

## Using Different LLM Providers

Just like with previous examples, you can use different LLM providers:

```python
import os
from mojentic.llm.gateways.openai import OpenAIGateway

# Set up OpenAI with a vision-capable model
api_key = os.getenv("OPENAI_API_KEY")
gateway = OpenAIGateway(api_key)
llm = LLMBroker(model="gpt-4o", gateway=gateway)

# Generate a response that includes image analysis
result = llm.generate(messages=[
    LLMMessage(
        content='What is in this image?',
        image_paths=[str(Path.cwd() / 'src' / '_examples' / 'images' / 'flash_rom.jpg')]
    )
])
```

## Summary

Image analysis with LLMs in Mojentic allows you to process and understand visual content alongside text. In this example, we've learned:

1. How to create messages that include images using the `image_paths` parameter
2. How to use multimodal models that can process both text and images
3. How to ask specific questions about images
4. How to work with multiple images

This capability enables a wide range of applications that combine visual and textual understanding, from content analysis to multimodal chatbots. By integrating image analysis with LLMs, you can build more versatile and powerful AI applications that can process and understand the world in a more human-like way.

Remember that different models have varying capabilities when it comes to image analysis. Some models are better at recognizing objects, while others excel at reading text or understanding complex scenes. Experiment with different models to find the one that best suits your specific use case.