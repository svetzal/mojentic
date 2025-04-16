from pathlib import Path

from mojentic.llm.message_composers import MessageBuilder

# Test de-duplication of images
print("Testing image de-duplication:")
image_path = Path.cwd() / 'src' / '_examples' / 'images' / 'xbox-one.jpg'

# Create a message builder and add the same image multiple times
message_builder = MessageBuilder("Testing image de-duplication")
message_builder.add_image(image_path)
message_builder.add_image(image_path)  # Adding the same image again
message_builder.add_images(image_path, image_path)  # Adding the same image twice more

# Build the message and check the number of images
message = message_builder.build()
print(f"Number of images in message: {len(message.image_paths)}")
print(f"Expected number of images: 1")
print(f"De-duplication working: {len(message.image_paths) == 1}")

# Test de-duplication of files
print("\nTesting file de-duplication:")
file_path = Path('file_deduplication.py')  # This file itself

# Create a message builder and add the same file multiple times
message_builder = MessageBuilder("Testing file de-duplication")
message_builder.add_file(file_path)
message_builder.add_file(file_path)  # Adding the same file again
message_builder.add_files(file_path, file_path)  # Adding the same file twice more

# Build the message and check the number of files
message = message_builder.build()
# Since we're using the file content in the message, we need to check file_paths directly
print(f"Number of files in message_builder.file_paths: {len(message_builder.file_paths)}")
print(f"Expected number of files: 1")
print(f"De-duplication working: {len(message_builder.file_paths) == 1}")

print("\nTest completed.")
