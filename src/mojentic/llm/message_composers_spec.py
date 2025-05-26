from pathlib import Path

import pytest

from mojentic.llm.gateways.models import LLMMessage, MessageRole
from mojentic.llm import MessageBuilder, FileTypeSensor


@pytest.fixture
def file_gateway(mocker):
    file_gateway = mocker.MagicMock()
    file_gateway.read.return_value = "test file content"
    file_gateway.exists.return_value = True
    file_gateway.is_binary.return_value = False
    return file_gateway

@pytest.fixture
def file_path():
    return Path("/path/to/file.txt")

@pytest.fixture
def whitespace_file_content():
    return "\n\n  \n  test file content with whitespace  \n\n  \n"


@pytest.fixture
def message_builder(file_gateway):
    builder = MessageBuilder()
    builder.file_gateway = file_gateway
    return builder


class DescribeMessageBuilder:
    """
    Specification for the MessageBuilder class which helps build LLM messages.
    """

    class DescribeInitialization:
        """
        Specifications for MessageBuilder initialization
        """

        def should_initialize_with_default_values(self):
            """
            Given a new MessageBuilder
            When it is initialized
            Then it should have default values set
            """
            builder = MessageBuilder()

            assert builder.role == MessageRole.User
            assert builder.content is None
            assert builder.image_paths == []
            assert builder.file_paths == []
            assert isinstance(builder.type_sensor, FileTypeSensor)
            assert isinstance(builder.file_gateway, object)

    class DescribeBuildMethod:
        """
        Specifications for the build method
        """

        def should_build_message_with_content(self, message_builder):
            message_builder.content = "Test content"

            message = message_builder.build()

            assert isinstance(message, LLMMessage)
            assert message.content == "Test content"
            assert message.role == MessageRole.User
            assert message.image_paths == []

        def should_build_message_with_role(self, message_builder):
            message_builder.role = MessageRole.Assistant

            message = message_builder.build()

            assert message.role == MessageRole.Assistant

        def should_build_message_with_image_paths(self, message_builder):
            message_builder.image_paths = [Path("/path/to/image1.jpg"), Path("/path/to/image2.jpg")]

            message = message_builder.build()

            assert message.image_paths == ["/path/to/image1.jpg", "/path/to/image2.jpg"]

        def should_build_message_with_file_content(self, message_builder, file_gateway):
            file_path = Path("/path/to/file.txt")
            message_builder.file_paths = [file_path]

            message = message_builder.build()

            file_gateway.read.assert_called_once_with(file_path)
            assert "test file content" in message.content
            assert "File: /path/to/file.txt" in message.content

        def should_build_message_with_multiple_file_contents(self, message_builder, file_gateway):
            file_path1 = Path("/path/to/file1.txt")
            file_path2 = Path("/path/to/file2.txt")
            message_builder.file_paths = [file_path1, file_path2]

            message = message_builder.build()

            assert file_gateway.read.call_count == 2
            assert "File: /path/to/file1.txt" in message.content
            assert "File: /path/to/file2.txt" in message.content

    class DescribeFileContentPartial:
        """
        Specifications for the _file_content_partial method
        """

        def should_format_file_content_with_language(self, message_builder, file_gateway, mocker):
            file_path = Path("/path/to/file.py")
            mocker.patch.object(message_builder.type_sensor, 'get_language', return_value='python')

            result = message_builder._file_content_partial(file_path)

            file_gateway.read.assert_called_once_with(file_path)
            assert "File: /path/to/file.py" in result
            assert "```python" in result
            assert "test file content" in result
            assert "```" in result

        def should_strip_whitespace_from_file_content(self, message_builder, file_gateway, file_path, whitespace_file_content, mocker):
            # Use the fixtures instead of creating file path and content directly
            file_gateway.read.return_value = whitespace_file_content
            mocker.patch.object(message_builder.type_sensor, 'get_language', return_value='text')

            result = message_builder._file_content_partial(file_path)

            file_gateway.read.assert_called_with(file_path)
            assert "File: /path/to/file.txt" in result
            assert "```text" in result
            assert "test file content with whitespace" in result
            assert "```" in result
            # Verify that the content in the code fence doesn't have leading/trailing whitespace
            lines = result.split('\n')
            code_fence_start_index = lines.index("```text")
            code_fence_end_index = lines.index("```", code_fence_start_index + 1)
            code_content = lines[code_fence_start_index + 1:code_fence_end_index]
            assert code_content == ["test file content with whitespace"]

    class DescribeAddImageMethod:
        """
        Specifications for the add_image method
        """

        def should_add_image_path_to_list(self, message_builder):
            image_path = Path("/path/to/image.jpg")

            result = message_builder.add_image(image_path)

            assert image_path in message_builder.image_paths
            assert result is message_builder  # Returns self for method chaining

        def should_convert_string_path_to_path_object(self, message_builder):
            image_path_str = "/path/to/image.jpg"

            message_builder.add_image(image_path_str)

            assert Path(image_path_str) in message_builder.image_paths

    class DescribeAddImagesMethod:
        """
        Specifications for the add_images method
        """

        def should_add_multiple_specific_images(self, message_builder):
            image_path1 = Path("/path/to/image1.jpg")
            image_path2 = Path("/path/to/image2.jpg")

            result = message_builder.add_images(image_path1, image_path2)

            assert image_path1 in message_builder.image_paths
            assert image_path2 in message_builder.image_paths
            assert result is message_builder  # Returns self for method chaining

        def should_add_all_jpg_images_from_directory(self, message_builder, mocker, tmp_path):
            # Create a temporary directory with test image files
            dir_path = tmp_path / "images"
            dir_path.mkdir()

            # Create empty test image files
            image1_path = dir_path / "image1.jpg"
            image2_path = dir_path / "image2.jpg"
            image1_path.touch()
            image2_path.touch()

            # Create a text file that should be ignored
            text_file_path = dir_path / "text.txt"
            text_file_path.touch()

            # Use the real directory for the test
            message_builder.add_images(dir_path)

            # Convert to strings for easier comparison
            image_paths_str = [str(p) for p in message_builder.image_paths]

            # Verify only jpg files were added
            assert str(image1_path) in image_paths_str
            assert str(image2_path) in image_paths_str
            assert str(text_file_path) not in image_paths_str

        def should_add_images_matching_glob_pattern(self, message_builder, tmp_path):
            # Create a temporary directory with test image files
            dir_path = tmp_path / "glob_test"
            dir_path.mkdir()

            # Create test image files
            image1_path = dir_path / "image1.jpg"
            image2_path = dir_path / "image2.jpg"
            image3_path = dir_path / "other.png"  # Should not match
            image1_path.touch()
            image2_path.touch()
            image3_path.touch()

            # Use a real glob pattern
            pattern_path = dir_path / "*.jpg"

            message_builder.add_images(pattern_path)

            # Convert to strings for easier comparison
            image_paths_str = [str(p) for p in message_builder.image_paths]

            # Verify only jpg files matching the pattern were added
            assert str(image1_path) in image_paths_str
            assert str(image2_path) in image_paths_str
            assert str(image3_path) not in image_paths_str

    class DescribeLoadContentMethod:
        """
        Specifications for the load_content method
        """

        def should_load_content_from_file(self, message_builder, file_gateway, file_path):
            result = message_builder.load_content(file_path)

            file_gateway.read.assert_called_once_with(file_path)
            assert message_builder.content == "test file content"
            assert result is message_builder  # Returns self for method chaining

        def should_convert_string_path_to_path_object(self, message_builder, file_gateway):
            file_path_str = "/path/to/file.txt"

            message_builder.load_content(file_path_str)

            file_gateway.read.assert_called_once_with(Path(file_path_str))

        def should_raise_error_if_file_not_found(self, message_builder, file_gateway, file_path):
            file_gateway.exists.return_value = False

            with pytest.raises(FileNotFoundError):
                message_builder.load_content(file_path)

        def should_replace_placeholders_with_template_values(self, message_builder, file_gateway, file_path):
            # Set up the file content with placeholders
            file_gateway.read.return_value = "Hello, {name}! Today is {day}."

            # Call load_content with template values
            template_values = {"name": "World", "day": "Monday"}
            result = message_builder.load_content(file_path, template_values)

            # Verify that placeholders were replaced
            assert message_builder.content == "Hello, World! Today is Monday."
            assert result is message_builder  # Returns self for method chaining


class DescribeTypeSensor:
    """
    Specification for the TypeSensor class which maps file extensions to language declarations.
    """

    def should_initialize_with_default_mappings(self):
        """
        Given a new TypeSensor
        When it is initialized
        Then it should have default mappings
        """
        sensor = FileTypeSensor()

        assert sensor.extension_map['py'] == 'python'
        assert sensor.extension_map['js'] == 'javascript'
        assert sensor.default_language == 'text'

    def should_get_language_for_known_extension(self):
        """
        Given a TypeSensor
        When get_language is called with a known extension
        Then it should return the correct language
        """
        sensor = FileTypeSensor()
        file_path = Path("/path/to/file.py")

        language = sensor.get_language(file_path)

        assert language == 'python'

    def should_get_default_language_for_unknown_extension(self):
        """
        Given a TypeSensor
        When get_language is called with an unknown extension
        Then it should return the default language
        """
        sensor = FileTypeSensor()
        file_path = Path("/path/to/file.unknown")

        language = sensor.get_language(file_path)

        assert language == 'text'

    def should_add_new_language_mapping(self):
        """
        Given a TypeSensor
        When add_language is called
        Then it should add the new mapping
        """
        sensor = FileTypeSensor()
        sensor.add_language('custom', 'customlang')

        assert sensor.extension_map['custom'] == 'customlang'

        file_path = Path("/path/to/file.custom")
        language = sensor.get_language(file_path)
        assert language == 'customlang'
