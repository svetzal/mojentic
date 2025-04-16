from pathlib import Path

from mojentic.llm import LLMBroker
from mojentic.llm.message_composers import MessageBuilder

# Initialize the LLM broker
llm = LLMBroker(model="gemma3:27b")

# Example 1: Adding multiple specific images using the splat operator
print("Example 1: Adding multiple specific images")
message1 = MessageBuilder("What are in these images?") \
    .add_images(
        Path.cwd() / 'images' / 'flash_rom.jpg',
        Path.cwd() / 'images' / 'screen_cap.png'  # Assuming this file exists
    ) \
    .build()

# Example 2: Adding all JPG images from a directory
print("\nExample 2: Adding all JPG images from a directory")
images_dir = Path.cwd() / 'images'
message2 = MessageBuilder("Describe all these images:") \
    .add_images(images_dir) \
    .build()

# Example 3: Using a glob pattern to add specific types of images
print("\nExample 3: Using a glob pattern")
message3 = MessageBuilder("What can you tell me about these images?") \
    .add_images(Path.cwd() / 'images' / '*.jpg') \
    .build()

# Example 4: Combining different ways to specify images
print("\nExample 4: Combining different ways to specify images")
message4 = MessageBuilder("Analyze these images:") \
    .add_images(
        Path.cwd() / 'images' / 'xbox-one.jpg',  # Specific image
        images_dir,                              # All JPGs in directory
        Path.cwd() / 'images' / '*.png'          # All PNGs using glob pattern
    ) \
    .build()

# Print the number of images added in each example
print(f"Example 1: Added {len(message1.image_paths)} image(s)")
print(f"Example 2: Added {len(message2.image_paths)} image(s)")
print(f"Example 3: Added {len(message3.image_paths)} image(s)")
print(f"Example 4: Added {len(message4.image_paths)} image(s)")

# Generate a response using one of the messages (e.g., message1)
print("\nGenerating response for Example 1...")
result = llm.generate(messages=[message1])
print(result)