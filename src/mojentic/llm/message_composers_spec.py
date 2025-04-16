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
            """
            Given a MessageBuilder with content
            When build is called
            Then it should return a message with that content
            """
            message_builder.content = "Test content"

            message = message_builder.build()

            assert isinstance(message, LLMMessage)
            assert message.content == "Test content"
            assert message.role == MessageRole.User
            assert message.image_paths == []

        def should_build_message_with_role(self, message_builder):
            """
            Given a MessageBuilder with a specific role
            When build is called
            Then it should return a message with that role
            """
            message_builder.role = MessageRole.Assistant

            message = message_builder.build()

            assert message.role == MessageRole.Assistant

        def should_build_message_with_image_paths(self, message_builder):
            """
            Given a MessageBuilder with image paths
            When build is called
            Then it should return a message with those image paths
            """
            message_builder.image_paths = [Path("/path/to/image1.jpg"), Path("/path/to/image2.jpg")]

            message = message_builder.build()

            assert message.image_paths == ["/path/to/image1.jpg", "/path/to/image2.jpg"]

        def should_build_message_with_file_content(self, message_builder, file_gateway):
            """
            Given a MessageBuilder with file paths
            When build is called
            Then it should return a message with the file contents
            """
            file_path = Path("/path/to/file.txt")
            message_builder.file_paths = [file_path]

            message = message_builder.build()

            file_gateway.read.assert_called_once_with(file_path)
            assert "test file content" in message.content
            assert "File: /path/to/file.txt" in message.content

        def should_build_message_with_multiple_file_contents(self, message_builder, file_gateway):
            """
            Given a MessageBuilder with multiple file paths
            When build is called
            Then it should return a message with all file contents
            """
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
            """
            Given a MessageBuilder
            When _file_content_partial is called
            Then it should format the file content with the correct language
            """
            file_path = Path("/path/to/file.py")
            mocker.patch.object(message_builder.type_sensor, 'get_language', return_value='python')

            result = message_builder._file_content_partial(file_path)

            file_gateway.read.assert_called_once_with(file_path)
            assert "File: /path/to/file.py" in result
            assert "```python" in result
            assert "test file content" in result
            assert "```" in result

        def should_strip_whitespace_from_file_content(self, message_builder, file_gateway, file_path, whitespace_file_content, mocker):
            """
            Given a MessageBuilder
            When _file_content_partial is called with content that has whitespace above and below
            Then it should strip the whitespace when putting it in code fences
            """
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
            """
            Given a MessageBuilder
            When add_image is called with a path
            Then it should add the path to the image_paths list
            """
            image_path = Path("/path/to/image.jpg")

            result = message_builder.add_image(image_path)

            assert image_path in message_builder.image_paths
            assert result is message_builder  # Returns self for method chaining

        def should_convert_string_path_to_path_object(self, message_builder):
            """
            Given a MessageBuilder
            When add_image is called with a string path
            Then it should convert the string to a Path object
            """
            image_path_str = "/path/to/image.jpg"

            message_builder.add_image(image_path_str)

            assert Path(image_path_str) in message_builder.image_paths

    class DescribeAddImagesMethod:
        """
        Specifications for the add_images method
        """

        def should_add_multiple_specific_images(self, message_builder):
            """
            Given a MessageBuilder
            When add_images is called with multiple specific image paths
            Then it should add all paths to the image_paths list
            """
            image_path1 = Path("/path/to/image1.jpg")
            image_path2 = Path("/path/to/image2.jpg")

            result = message_builder.add_images(image_path1, image_path2)

            assert image_path1 in message_builder.image_paths
            assert image_path2 in message_builder.image_paths
            assert result is message_builder  # Returns self for method chaining

        def should_add_all_jpg_images_from_directory(self, message_builder, mocker):
            """
            Given a MessageBuilder
            When add_images is called with a directory path
            Then it should add all JPG images in that directory
            """
            dir_path = Path("/path/to/images")
            jpg_files = [Path("/path/to/images/image1.jpg"), Path("/path/to/images/image2.jpg")]

            # Mock is_dir, glob, and exists methods
            mocker.patch.object(Path, 'is_dir', return_value=True)
            mocker.patch.object(Path, 'glob', return_value=jpg_files)
            mocker.patch.object(Path, 'exists', return_value=True)

            message_builder.add_images(dir_path)

            assert jpg_files[0] in message_builder.image_paths
            assert jpg_files[1] in message_builder.image_paths

        def should_add_images_matching_glob_pattern(self, message_builder, mocker):
            """
            Given a MessageBuilder
            When add_images is called with a path containing a wildcard
            Then it should add all matching files
            """
            pattern_path = Path("/path/to/*.jpg")
            matching_files = [Path("/path/to/image1.jpg"), Path("/path/to/image2.jpg")]

            # Mock methods
            mocker.patch.object(Path, 'is_dir', return_value=False)
            mocker.patch.object(Path, 'glob', return_value=matching_files)
            mocker.patch.object(Path, 'is_file', return_value=True)
            mocker.patch.object(Path, 'exists', return_value=True)

            # Mock the parent property and its glob method
            parent_mock = mocker.MagicMock()
            parent_mock.glob.return_value = matching_files
            mocker.patch.object(Path, 'parent', parent_mock)

            message_builder.add_images(pattern_path)

            assert matching_files[0] in message_builder.image_paths
            assert matching_files[1] in message_builder.image_paths

    class DescribeLoadContentMethod:
        """
        Specifications for the load_content method
        """

        def should_load_content_from_file(self, message_builder, file_gateway, file_path):
            """
            Given a MessageBuilder
            When load_content is called with a file path
            Then it should load the content from the file and set it as the content
            """
            result = message_builder.load_content(file_path)

            file_gateway.read.assert_called_once_with(file_path)
            assert message_builder.content == "test file content"
            assert result is message_builder  # Returns self for method chaining

        def should_convert_string_path_to_path_object(self, message_builder, file_gateway):
            """
            Given a MessageBuilder
            When load_content is called with a string path
            Then it should convert the string to a Path object
            """
            file_path_str = "/path/to/file.txt"

            message_builder.load_content(file_path_str)

            file_gateway.read.assert_called_once_with(Path(file_path_str))

        def should_raise_error_if_file_not_found(self, message_builder, file_gateway, file_path):
            """
            Given a MessageBuilder
            When load_content is called with a non-existent file
            Then it should raise a FileNotFoundError
            """
            file_gateway.exists.return_value = False

            with pytest.raises(FileNotFoundError):
                message_builder.load_content(file_path)

        def should_replace_placeholders_with_template_values(self, message_builder, file_gateway, file_path):
            """
            Given a MessageBuilder
            When load_content is called with a file path and template values
            Then it should replace placeholders in the content with the corresponding values
            """
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
