# MessageBuilder

The `MessageBuilder` class simplifies the creation of messages with text, images, and file contents. This builder pattern makes it easy to construct complex messages with a fluent interface.

## Usage Example

```python
from mojentic.llm import LLMBroker
from mojentic.llm.message_composer import MessageBuilder
from pathlib import Path

# Create an LLM broker
llm = LLMBroker(model="gemma3:27b")

# Build a message with text, an image, and a file
message = MessageBuilder("Please analyze this image and code:")\
    .add_image(Path.cwd() / "images" / "example.jpg")\
    .add_file(Path.cwd() / "src" / "example.py")\
    .build()

# Generate a response
result = llm.generate(messages=[message])
print(result)
```

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

::: mojentic.llm.message_composer.MessageBuilder
    options:
        show_root_heading: true
        merge_init_into_class: false
        group_by_category: false