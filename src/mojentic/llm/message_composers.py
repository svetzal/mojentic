from pathlib import Path
from typing import Union, Dict, List, Optional

from mojentic.llm.gateways.file_gateway import FileGateway
from mojentic.llm.gateways.models import LLMMessage, MessageRole


class FileTypeSensor:
    """Maps file extensions to language declarations for markdown code-fence."""

    def __init__(self):
        """
        Initialize the TypeSensor with a default mapping of file extensions to language declarations.

        The TypeSensor is used to determine the appropriate language syntax highlighting 
        for code blocks in markdown based on file extensions.
        """
        self.extension_map: Dict[str, str] = {
            'c': 'c',
            'cpp': 'c++',
            'c++': 'c++',
            'cxx': 'c++',
            'h': 'c',
            'objc': 'objective-c',
            'swift': 'swift',
            'cs': 'csharp',
            'fs': 'fsharp',
            'clj': 'clojure',
            'py': 'python',
            'java': 'java',
            'kt': 'kotlin',
            'rb': 'ruby',
            'js': 'javascript',
            'ts': 'typescript',
            'rs': 'rust',
            'go': 'go',
            'cbl': 'cobol',
            'html': 'html',
            'css': 'css',
            'json': 'json',
            'csv': 'csv',
            'xml': 'xml',
            'md': 'markdown',
        }
        self.default_language = 'text'

    def add_language(self, extension: str, language: str):
        """
        Add or update a mapping from a file extension to a language declaration.

        Parameters
        ----------
        extension : str
            The file extension without the leading dot (e.g., 'py', 'js')
        language : str
            The language identifier for markdown code-fence (e.g., 'python', 'javascript')
        """
        self.extension_map[extension] = language

    def get_language(self, file_path: Path) -> str:
        """
        Determine the language declaration for a file based on its extension.

        Parameters
        ----------
        file_path : Path
            Path to the file

        Returns
        -------
        str
            Language declaration for markdown code-fence
        """
        ext = file_path.suffix[1:]  # Remove the leading dot
        return self.extension_map.get(ext, self.default_language)


class MessageBuilder():
    """
    A builder class for creating LLM messages with text content, images, and files.

    This class provides a fluent interface for constructing messages to be sent to an LLM,
    with support for adding text content, images, and file contents. It handles file reading,
    language detection for syntax highlighting, and proper formatting of the message.
    """
    role: MessageRole
    content: Optional[str]
    image_paths: List[Path]
    file_paths: List[Path]
    type_sensor: FileTypeSensor

    def __init__(self, content: str = None):
        """
        Initialize a new MessageBuilder with optional text content.

        Parameters
        ----------
        content : str, optional
            Optional text content for the message. If None, the message will only
            contain added files and images.
        """
        self.role = MessageRole.User
        self.content = content
        self.image_paths = []
        self.file_paths = []
        self.type_sensor = FileTypeSensor()
        self.file_gateway = FileGateway()

    def _file_content_partial(self, file_path: Path) -> str:
        """
        Format the content of a file for inclusion in the message.

        This method reads the file content and formats it with appropriate markdown code-fence
        syntax highlighting based on the file extension.

        Parameters
        ----------
        file_path : Path
            Path to the file to be read and formatted

        Returns
        -------
        str
            Formatted string containing the file path and content with markdown code-fence
        """
        content = self.file_gateway.read(file_path)
        return (f"File: {file_path}\n"
                f"```{self.type_sensor.get_language(file_path)}\n"
                f"{content.strip()}\n"
                f"```\n")


    def add_image(self, image_path: Union[str, Path]) -> "MessageBuilder":
        """
        Add a single image to the message.

        Parameters
        ----------
        image_path : Union[str, Path]
            Path to the image file. Can be a string or Path object.

        Returns
        -------
        MessageBuilder
            The MessageBuilder instance for method chaining.

        Raises
        ------
        FileNotFoundError
            If the specified image file does not exist.
        """
        if isinstance(image_path, str):
            image_path = Path(image_path)
        if not self.file_gateway.exists(image_path):
            raise FileNotFoundError(f"Image file not found: {image_path}")
        if image_path not in self.image_paths:
            self.image_paths.append(image_path)
        return self

    def add_file(self, file_path: Union[str, Path]) -> "MessageBuilder":
        """
        Add a single file to the message.

        Parameters
        ----------
        file_path : Union[str, Path]
            Path to the file. Can be a string or Path object.

        Returns
        -------
        MessageBuilder
            The MessageBuilder instance for method chaining.

        Raises
        ------
        FileNotFoundError
            If the specified file does not exist.
        """
        if isinstance(file_path, str):
            file_path = Path(file_path)
        if not self.file_gateway.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
        if file_path not in self.file_paths:
            self.file_paths.append(file_path)
        return self

    def add_images(self, *image_paths: Union[str, Path]) -> "MessageBuilder":
        """
        Add multiple images to the message.

        Parameters
        ----------
        *image_paths : Union[str, Path]
            Variable number of image paths. Can be strings or Path objects.
            Can include glob patterns like '*.jpg' to include all JPG and PNG images in a directory.

        Returns
        -------
        MessageBuilder
            The MessageBuilder instance for method chaining.
        """
        for path in image_paths:
            path_obj = Path(path) if isinstance(path, str) else path

            if path_obj.is_dir():
                for ext in ['*.jpg', '*.png']:
                    for img_path in path_obj.glob(ext):
                        self.add_image(img_path)
            elif '*' in str(path_obj):
                parent_dir = path_obj.parent if path_obj.parent != Path('.') else Path.cwd()
                for img_path in parent_dir.glob(path_obj.name):
                    if img_path.is_file():
                        self.add_image(img_path)
            else:
                self.add_image(path_obj)

        return self

    def add_files(self, *file_paths: List[Union[str, Path]]) -> "MessageBuilder":
        """
        Add multiple text files to the message, ignoring binary files.

        Parameters
        ----------
        *file_paths : Union[str, Path]
            Variable number of file paths. Can be strings or Path objects.
            Can include glob patterns like '*.txt' to include all text files in a directory.
            If a directory is provided, all text files in the directory will be added.

        Returns
        -------
        MessageBuilder
            The MessageBuilder instance for method chaining.
        """
        for path in file_paths:
            path_obj = Path(path) if isinstance(path, str) else path

            if path_obj.is_dir():
                # If a directory is provided, add all text files in the directory
                for file_path in path_obj.glob('*'):
                    if file_path.is_file() and not self.file_gateway.is_binary(file_path):
                        self.add_file(file_path)
            elif '*' in str(path_obj):
                # If a glob pattern is provided, add all matching text files
                parent_dir = path_obj.parent if path_obj.parent != Path('.') else Path.cwd()
                for file_path in parent_dir.glob(path_obj.name):
                    if file_path.is_file() and not self.file_gateway.is_binary(file_path):
                        self.add_file(file_path)
            else:
                # If a single file is provided, add it if it's a text file
                if path_obj.is_file() and not self.file_gateway.is_binary(path_obj):
                    self.add_file(path_obj)

        return self

    def load_content(self, file_path: Union[str, Path], template_values: Optional[Dict[str, Union[str, Path]]] = None) -> "MessageBuilder":
        """
        Load content from a file into the content field of the MessageBuilder.

        This method reads the content of the specified file and sets it as the content
        of the MessageBuilder, replacing any existing content. If template_values is provided,
        placeholders in the content will be replaced with the corresponding values.

        Parameters
        ----------
        file_path : Union[str, Path]
            Path to the file to load content from. Can be a string or Path object.
        template_values : Optional[Dict[str, Union[str, Path]]], optional
            Dictionary of values used to replace placeholders in the content.
            For example, if the content contains "{greeting}" and template_values is
            {"greeting": "Hello, World!"}, then "{greeting}" will be replaced with
            "Hello, World!".
            If a value is a Path object, it will be treated as a file reference and the
            content of that file will be used to replace the placeholder.
            Default is None.

        Returns
        -------
        MessageBuilder
            The MessageBuilder instance for method chaining.

        Raises
        ------
        FileNotFoundError
            If the specified file does not exist.
        """
        if isinstance(file_path, str):
            file_path = Path(file_path)
        if not self.file_gateway.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
        self.content = self.file_gateway.read(file_path)

        # Replace placeholders with template values if provided
        if template_values:
            for key, value in template_values.items():
                if isinstance(value, Path):
                    # If value is a Path, read the content of the file
                    if not self.file_gateway.exists(value):
                        raise FileNotFoundError(f"Template file not found: {value}")
                    file_content = self.file_gateway.read(value).strip()
                    self.content = self.content.replace(f"{{{key}}}", file_content)
                else:
                    # If value is a string, use it directly
                    self.content = self.content.replace(f"{{{key}}}", value)

        return self

    def build(self) -> LLMMessage:
        """
        Build the final LLMMessage from the accumulated content, images, and files.

        This method combines all the content, file contents, and image paths into a single
        LLMMessage object that can be sent to an LLM. If files have been added, their contents
        will be formatted and included in the message content.

        Returns
        -------
        LLMMessage
            An LLMMessage object containing the message content and image paths.
        """
        parts = []
        if self.file_paths:
            file_contents = [self._file_content_partial(p) for p in self.file_paths]
            parts.append("\n\n".join(file_contents))
        if self.content is not None:
            parts.append(self.content)
        return LLMMessage(
            role=self.role,
            content="\n\n".join(parts),
            image_paths=[str(p) for p in self.image_paths]
        )
