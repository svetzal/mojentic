# MessageBuilder

The `MessageBuilder` class simplifies the creation of messages with text, images, and file contents. This builder pattern makes it easy to construct complex messages with a fluent interface.

## Usage Examples

### Simple Image Analysis

This example shows how to analyze a single image using a multimodal LLM:

```python
from mojentic.llm import LLMBroker
from mojentic.llm import MessageBuilder
from pathlib import Path

# Create an LLM broker with a multimodal model
llm = LLMBroker(model="gemma3:27b")

# Build a message with a single image
message = MessageBuilder("Please analyze this image and describe what you see:") \
    .add_image(Path.cwd() / "images" / "flash_rom.jpg") \
    .build()

# Generate a response
result = llm.generate(messages=[message])
print(result)
```

### Comparing Two Images

This example demonstrates how to compare two images:

```python
from mojentic.llm import LLMBroker
from mojentic.llm import MessageBuilder
from pathlib import Path

# Create an LLM broker
llm = LLMBroker(model="gemma3:27b")

# Build a message with two images for comparison
message = MessageBuilder("Compare these two images and tell me the differences:") \
    .add_image(Path.cwd() / "images" / "image1.jpg") \
    .add_image(Path.cwd() / "images" / "image2.jpg") \
    .build()

# Generate a response
result = llm.generate(messages=[message])
print(result)
```

### Converting Java to Kotlin

This example shows how to use an LLM to convert a Java file to Kotlin:

```python
from mojentic.llm import LLMBroker
from mojentic.llm import MessageBuilder
from pathlib import Path

# Create an LLM broker
llm = LLMBroker(model="gemma3:27b")

# Build a message with a Java file
message = MessageBuilder("Convert this Java code to Kotlin, maintaining the same functionality:") \
    .add_file(Path.cwd() / "src" / "example.java") \
    .build()

# Generate a response
result = llm.generate(messages=[message])
print(result)
```

### Processing Multiple Markdown Documents

This example demonstrates how to summarize the contents of multiple markdown documents in a folder:

```python
from mojentic.llm import LLMBroker
from mojentic.llm import MessageBuilder
from pathlib import Path

# Create an LLM broker
llm = LLMBroker(model="gemma3:27b")

# Build a message with multiple markdown files from a folder
message = MessageBuilder("Summarize the key points from these markdown documents:") \
    .add_files(Path.cwd() / "docs" / "*.md") \
    .build()

# Generate a response
result = llm.generate(messages=[message])
print(result)
```

## Important Considerations

### LLM Context Size Limitations

When adding multiple files or large images to a message, be aware of LLM context size limitations:

- **Context Window Limits**: Each LLM has a maximum context window size (e.g., 8K, 16K, 32K tokens).
- **Performance Impact**: Adding too much data to messages will slow down the LLM's processing time.
- **Request Failures**: Exceeding the context limit will cause the request to fail with an error.
- **Selective Content**: Only include the most relevant files and images in your messages.
- **File Size**: Large files may need to be split or summarized before processing.

For large datasets:
- Consider chunking files into smaller segments
- Process files sequentially rather than all at once
- Use specialized document processing tools for very large documents

## Key Features

- **Fluent Interface**: Chain method calls for a clean, readable syntax
- **Multiple Content Types**: Add text, images, and files to a single message
- **File Content Formatting**: Automatically formats file contents with appropriate syntax highlighting
- **Type Detection**: Detects file types and applies appropriate language tags for code blocks
- **Path Flexibility**: Accepts both string paths and Path objects

## Important Methods

- **add_image()**: Add a single image to the message
- **add_images()**: Add multiple images at once, with support for glob patterns
- **add_file()**: Add a single file's content to the message
- **add_files()**: Add multiple files at once, with support for glob patterns
- **build()**: Create the final LLMMessage object to send to the LLM

## API Reference

::: mojentic.llm.MessageBuilder
    options:
        show_root_heading: true
        merge_init_into_class: false
        group_by_category: false
