from pathlib import Path
import sys
import os

from mojentic.llm.message_composers import MessageBuilder

# Get the project root directory (2 levels up from the current script)
project_root = Path(os.path.dirname(os.path.abspath(__file__))).parent.parent

# Test adding non-existent image
print("Testing adding non-existent image:")
non_existent_image = project_root / 'src' / '_examples' / 'images' / 'non_existent_image.jpg'

try:
    message_builder = MessageBuilder("Testing non-existent image")
    message_builder.add_image(non_existent_image)
    print("ERROR: Expected FileNotFoundError was not raised")
    sys.exit(1)
except FileNotFoundError as e:
    print(f"Success: Caught expected exception: {e}")

# Test adding non-existent file
print("\nTesting adding non-existent file:")
non_existent_file = project_root / 'src' / '_examples' / 'non_existent_file.py'

try:
    message_builder = MessageBuilder("Testing non-existent file")
    message_builder.add_file(non_existent_file)
    print("ERROR: Expected FileNotFoundError was not raised")
    sys.exit(1)
except FileNotFoundError as e:
    print(f"Success: Caught expected exception: {e}")

# Test adding existing image
print("\nTesting adding existing image:")
existing_image = project_root / 'src' / '_examples' / 'images' / 'xbox-one.jpg'

try:
    message_builder = MessageBuilder("Testing existing image")
    message_builder.add_image(existing_image)
    print("Success: Added existing image without exception")
except FileNotFoundError as e:
    print(f"ERROR: Unexpected exception: {e}")
    sys.exit(1)

# Test adding existing file
print("\nTesting adding existing file:")
existing_file = Path(__file__)  # This file itself (absolute path)

try:
    message_builder = MessageBuilder("Testing existing file")
    message_builder.add_file(existing_file)
    print("Success: Added existing file without exception")
except FileNotFoundError as e:
    print(f"ERROR: Unexpected exception: {e}")
    sys.exit(1)

print("\nAll tests passed!")
