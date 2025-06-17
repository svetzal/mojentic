import os
import re
import glob
import difflib

from mojentic.llm.tools.llm_tool import LLMTool


class FilesystemGateway:
    def __init__(self, base_path: str):
        self.base_path = base_path

    def _resolve_path(self, path: str) -> str:
        """Resolve a path relative to the base path."""
        # Ensure the path is within the sandbox
        resolved_path = os.path.normpath(os.path.join(self.base_path, path))
        # Verify the path is within the sandbox
        if not resolved_path.startswith(os.path.normpath(self.base_path)):
            raise ValueError(f"Path {path} attempts to escape the sandbox")
        return resolved_path

    def ls(self, path: str) -> list[str]:
        resolved_path = self._resolve_path(path)
        files = os.listdir(resolved_path)

        # Convert the filenames to paths relative to the base_path using list comprehension
        relative_files = [os.path.relpath(os.path.join(resolved_path, file), self.base_path)
                          for file in files]

        return relative_files

    def list_all_files(self, path: str) -> list[str]:
        """List all files recursively in the given path."""
        resolved_path = self._resolve_path(path)
        all_files = []

        for root, _, files in os.walk(resolved_path):
            for file in files:
                full_path = os.path.join(root, file)
                relative_path = os.path.relpath(full_path, self.base_path)
                all_files.append(relative_path)

        return all_files

    def find_files_by_glob(self, path: str, pattern: str) -> list[str]:
        """Find files matching a glob pattern."""
        resolved_path = self._resolve_path(path)
        # Use glob to find files matching the pattern
        matching_files = glob.glob(os.path.join(resolved_path, pattern), recursive=True)

        # Convert to paths relative to base_path
        relative_files = [os.path.relpath(file, self.base_path) for file in matching_files]
        return relative_files

    def find_files_containing(self, path: str, pattern: str) -> list[str]:
        """Find files containing text matching a regex pattern."""
        resolved_path = self._resolve_path(path)
        matching_files = []
        regex = re.compile(pattern)

        for root, _, files in os.walk(resolved_path):
            for file in files:
                full_path = os.path.join(root, file)
                try:
                    with open(full_path, 'r', errors='ignore') as f:
                        content = f.read()
                        if regex.search(content):
                            relative_path = os.path.relpath(full_path, self.base_path)
                            matching_files.append(relative_path)
                except (IOError, UnicodeDecodeError):
                    # Skip files that can't be read as text
                    pass

        return matching_files

    def find_lines_matching(self, path: str, file_name: str, pattern: str) -> list[dict]:
        """Find all lines in a file matching a regex pattern."""
        resolved_path = self._resolve_path(path)
        file_path = os.path.join(resolved_path, file_name)
        matching_lines = []
        regex = re.compile(pattern)

        try:
            with open(file_path, 'r', errors='ignore') as f:
                for i, line in enumerate(f, 1):
                    if regex.search(line):
                        matching_lines.append({
                            'line_number': i,
                            'content': line.rstrip('\n')
                        })
        except (IOError, UnicodeDecodeError) as e:
            raise ValueError(f"Error reading file {file_name}: {str(e)}")

        return matching_lines


    def edit_file_with_diff(self, path: str, file_name: str, diff: str) -> str:
        """Edit a file by applying a diff to it."""
        resolved_path = self._resolve_path(path)
        file_path = os.path.join(resolved_path, file_name)

        try:
            # Read the original content
            with open(file_path, 'r') as f:
                original_content = f.read()

            # Check if the original file ends with a newline
            ends_with_newline = original_content.endswith('\n')

            # Apply the diff using difflib's unified_diff parser
            original_lines = original_content.splitlines()
            patched_content = self._apply_unified_diff(original_lines, diff)

            # Preserve the trailing newline if it existed
            if ends_with_newline and not patched_content.endswith('\n'):
                patched_content += '\n'

            # Write the modified content
            with open(file_path, 'w') as f:
                f.write(patched_content)

            return f"Successfully applied diff to {file_name}"
        except Exception as e:
            raise ValueError(f"Error applying diff to {file_name}: {str(e)}")

    def _apply_unified_diff(self, original_lines, diff_text):
        """Apply a unified diff to the original lines."""
        # Split the diff into lines
        diff_lines = diff_text.splitlines()

        # Create a copy of the original lines to modify
        result_lines = original_lines.copy()

        # Parse the diff and apply changes
        i = 0
        while i < len(diff_lines):
            line = diff_lines[i]

            # Skip file headers
            if line.startswith('---') or line.startswith('+++'):
                i += 1
                continue

            # Parse hunk header
            if line.startswith('@@'):
                # Format: @@ -start,count +start,count @@
                match = re.match(r'@@ -(\d+),(\d+) \+(\d+),(\d+) @@', line)
                if not match:
                    # Try alternative format without counts
                    match = re.match(r'@@ -(\d+) \+(\d+) @@', line)
                    if match:
                        start_line = int(match.group(1))
                        start_line_new = int(match.group(2))
                    else:
                        # Skip invalid hunk header
                        i += 1
                        continue
                else:
                    start_line = int(match.group(1))
                    start_line_new = int(match.group(3))

                # Line numbers in diff are 1-based, but our array is 0-based
                start_line -= 1

                # Extract the hunk content
                hunk_lines = []
                i += 1
                while i < len(diff_lines) and not diff_lines[i].startswith('@@'):
                    hunk_lines.append(diff_lines[i])
                    i += 1

                # Apply this hunk
                self._apply_hunk(result_lines, hunk_lines, start_line)
                continue

            i += 1

        # Join the result lines into a single string
        return '\n'.join(result_lines)

    def _apply_hunk(self, result_lines, hunk_lines, start_line):
        """Apply a single hunk to the result_lines list."""
        # Find the actual position in the file by matching context lines
        actual_pos = self._find_hunk_position(result_lines, hunk_lines, start_line)
        if actual_pos == -1:
            # Could not find the position, use the start_line as a fallback
            actual_pos = start_line

        # Apply the changes
        removed = 0
        added = 0
        pos = actual_pos

        for line in hunk_lines:
            if line.startswith('-'):
                # Remove line
                if pos < len(result_lines):
                    result_lines.pop(pos)
                    removed += 1
                # Don't increment pos as we're removing this line
            elif line.startswith('+'):
                # Add line
                result_lines.insert(pos, line[1:])
                pos += 1
                added += 1
            else:
                # Context line (unchanged)
                if line.startswith(' '):
                    line = line[1:]
                pos += 1

    def _find_hunk_position(self, result_lines, hunk_lines, start_line):
        """Find the actual position of a hunk in the file by matching context lines."""
        # Extract context lines from the beginning of the hunk
        context_lines = []
        for line in hunk_lines:
            if line.startswith(' '):
                context_lines.append(line[1:])
            else:
                break

        if not context_lines:
            return start_line

        # Try to find the context lines in the file
        for i in range(max(0, start_line - 10), min(len(result_lines), start_line + 10)):
            if i + len(context_lines) <= len(result_lines):
                match = True
                for j, context_line in enumerate(context_lines):
                    if result_lines[i + j] != context_line:
                        match = False
                        break
                if match:
                    return i

        return -1

    def read(self, path: str, file_name: str) -> str:
        resolved_path = self._resolve_path(path)
        with open(os.path.join(resolved_path, file_name), 'r') as f:
            return f.read()

    def write(self, path: str, file_name: str, content: str) -> None:
        resolved_path = self._resolve_path(path)
        with open(os.path.join(resolved_path, file_name), 'w') as f:
            f.write(content)


class FileManager:
    def __init__(self, fs: FilesystemGateway):
        self.fs = fs

    def ls(self, path: str, extension: str = None) -> list[str]:
        entries = self.fs.ls(path)
        if extension is None:
            return entries
        return [f for f in entries if f.endswith(extension)]

    def list_all_files(self, path: str) -> list[str]:
        """List all files recursively in the sandbox."""
        return self.fs.list_all_files(path)

    def find_files_by_glob(self, path: str, pattern: str) -> list[str]:
        """Find files matching a glob pattern."""
        return self.fs.find_files_by_glob(path, pattern)

    def find_files_containing(self, path: str, pattern: str) -> list[str]:
        """Find files containing text matching a regex pattern."""
        return self.fs.find_files_containing(path, pattern)

    def find_lines_matching(self, path: str, file_name: str, pattern: str) -> list[dict]:
        """Find all lines in a file matching a regex pattern."""
        return self.fs.find_lines_matching(path, file_name, pattern)

    def edit_file_with_diff(self, path: str, file_name: str, diff: str) -> str:
        """Edit a file by applying a diff to it."""
        return self.fs.edit_file_with_diff(path, file_name, diff)

    def read(self, path: str, file_name: str) -> str:
        return self.fs.read(path, file_name)

    def write(self, path: str, file_name: str, content: str) -> None:
        self.fs.write(path, file_name, content)


class ListFilesTool(LLMTool):
    def __init__(self, fs: FilesystemGateway):
        self.fs = fs

    def run(self, path: str, extension: str = None) -> list[str]:
        try:
            entries = self.fs.ls(path)
            if extension is None:
                return entries
            return [f for f in entries if f.endswith(extension)]
        except ValueError as e:
            return f"Error: {str(e)}"
        except FileNotFoundError:
            return f"Error: Directory '{path}' not found"
        except PermissionError:
            return f"Error: Permission denied when accessing directory '{path}'"
        except Exception as e:
            return f"Error listing files in '{path}': {str(e)}"

    @property
    def descriptor(self):
        return {
            "type": "function",
            "function": {
                "name": "list_files",
                "description": "List files in the specified directory (non-recursive), optionally filtered by extension. Use this when you need to see what files are available in a specific directory without including subdirectories.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "The path relative to the sandbox root to list files from. For example, '.' for the root directory, 'src' for the src directory, or 'docs/images' for a nested directory."
                        },
                        "extension": {
                            "type": "string",
                            "description": "The file extension to filter by (e.g., '.py', '.txt', '.md'). If not provided, all files will be listed. For example, using '.py' will only list Python files in the directory."
                        }
                    },
                    "additionalProperties": False,
                    "required": ["path"]
                },
            },
        }


class ReadFileTool(LLMTool):
    def __init__(self, fs: FilesystemGateway):
        self.fs = fs

    def run(self, path: str) -> str:
        try:
            # Split the path into directory and filename
            directory, file_name = os.path.split(path)
            return self.fs.read(directory, file_name)
        except ValueError as e:
            return f"Error: {str(e)}"
        except FileNotFoundError:
            return f"Error: File '{path}' not found"
        except PermissionError:
            return f"Error: Permission denied when accessing file '{path}'"
        except IOError as e:
            return f"Error reading file '{path}': {str(e)}"
        except UnicodeDecodeError:
            return f"Error: File '{path}' contains non-text content that cannot be read as text"
        except Exception as e:
            return f"Error reading file '{path}': {str(e)}"

    @property
    def descriptor(self):
        return {
            "type": "function",
            "function": {
                "name": "read_file",
                "description": "Read the entire content of a file as a string. Use this when you need to access or analyze the complete contents of a file.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "The full relative path including the filename of the file to read. For example, 'README.md' for a file in the root directory, 'src/main.py' for a file in the src directory, or 'docs/images/diagram.png' for a file in a nested directory."
                        }
                    },
                    "additionalProperties": False,
                    "required": ["path"]
                },
            },
        }


class WriteFileTool(LLMTool):
    def __init__(self, fs: FilesystemGateway):
        self.fs = fs

    def run(self, path: str, content: str) -> str:
        try:
            # Split the path into directory and filename
            directory, file_name = os.path.split(path)
            self.fs.write(directory, file_name, content)
            return f"Successfully wrote to {path}"
        except ValueError as e:
            return f"Error: {str(e)}"
        except FileNotFoundError:
            return f"Error: Directory not found. Cannot write file '{path}'"
        except PermissionError:
            return f"Error: Permission denied when writing to file '{path}'"
        except IOError as e:
            return f"Error writing to file '{path}': {str(e)}"
        except Exception as e:
            return f"Error writing to file '{path}': {str(e)}"

    @property
    def descriptor(self):
        return {
            "type": "function",
            "function": {
                "name": "write_file",
                "description": "Write content to a file, completely overwriting any existing content. Use this when you want to replace the entire contents of a file with new content.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "The full relative path including the filename where the file should be written. For example, 'output.txt' for a file in the root directory, 'src/main.py' for a file in the src directory, or 'docs/images/diagram.png' for a file in a nested directory."
                        },
                        "content": {
                            "type": "string",
                            "description": "The content to write to the file. This will completely replace any existing content in the file. For example, 'Hello, world!' for a simple text file, or a JSON string for a configuration file."
                        }
                    },
                    "additionalProperties": False,
                    "required": ["path", "content"]
                },
            },
        }


class ListAllFilesTool(LLMTool):
    def __init__(self, fs: FilesystemGateway):
        self.fs = fs

    def run(self, path: str) -> list[str]:
        try:
            return self.fs.list_all_files(path)
        except ValueError as e:
            return f"Error: {str(e)}"
        except FileNotFoundError:
            return f"Error: Directory '{path}' not found"
        except PermissionError:
            return f"Error: Permission denied when accessing directory '{path}'"
        except Exception as e:
            return f"Error listing files recursively in '{path}': {str(e)}"

    @property
    def descriptor(self):
        return {
            "type": "function",
            "function": {
                "name": "list_all_files",
                "description": "List all files recursively in the specified directory, including files in subdirectories. Use this when you need a complete inventory of all files in a directory and its subdirectories.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "The path relative to the sandbox root to list files from recursively. For example, '.' for the root directory and all subdirectories, 'src' for the src directory and all its subdirectories, or 'docs/images' for a nested directory and its subdirectories."
                        }
                    },
                    "additionalProperties": False,
                    "required": ["path"]
                },
            },
        }


class FindFilesByGlobTool(LLMTool):
    def __init__(self, fs: FilesystemGateway):
        self.fs = fs

    def run(self, path: str, pattern: str) -> list[str]:
        try:
            return self.fs.find_files_by_glob(path, pattern)
        except ValueError as e:
            return f"Error: {str(e)}"
        except FileNotFoundError:
            return f"Error: Directory '{path}' not found"
        except PermissionError:
            return f"Error: Permission denied when accessing directory '{path}'"
        except Exception as e:
            return f"Error finding files with pattern '{pattern}' in '{path}': {str(e)}"

    @property
    def descriptor(self):
        return {
            "type": "function",
            "function": {
                "name": "find_files_by_glob",
                "description": "Find files matching a glob pattern in the specified directory. Use this when you need to locate files with specific patterns in their names or paths (e.g., all Python files with '*.py' or all text files in any subdirectory with '**/*.txt').",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "The path relative to the sandbox root to search in. For example, '.' for the root directory, 'src' for the src directory, or 'docs/images' for a nested directory."
                        },
                        "pattern": {
                            "type": "string",
                            "description": "The glob pattern to match files against. Examples: '*.py' for all Python files in the specified directory, '**/*.txt' for all text files in the specified directory and any subdirectory, or '**/*test*.py' for all Python files with 'test' in their name in the specified directory and any subdirectory."
                        }
                    },
                    "additionalProperties": False,
                    "required": ["path", "pattern"]
                },
            },
        }


class FindFilesContainingTool(LLMTool):
    def __init__(self, fs: FilesystemGateway):
        self.fs = fs

    def run(self, path: str, pattern: str) -> list[str]:
        try:
            return self.fs.find_files_containing(path, pattern)
        except ValueError as e:
            return f"Error: {str(e)}"
        except FileNotFoundError:
            return f"Error: Directory '{path}' not found"
        except PermissionError:
            return f"Error: Permission denied when accessing directory '{path}'"
        except re.error as e:
            return f"Error: Invalid regex pattern '{pattern}': {str(e)}"
        except Exception as e:
            return f"Error finding files containing pattern '{pattern}' in '{path}': {str(e)}"

    @property
    def descriptor(self):
        return {
            "type": "function",
            "function": {
                "name": "find_files_containing",
                "description": "Find files containing text matching a regex pattern in the specified directory. Use this when you need to search for specific content across multiple files, such as finding all files that contain a particular function name or text string.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "The path relative to the sandbox root to search in. For example, '.' for the root directory, 'src' for the src directory, or 'docs/images' for a nested directory."
                        },
                        "pattern": {
                            "type": "string",
                            "description": "The regex pattern to search for in files. Examples: 'function\\s+main' to find files containing a main function, 'import\\s+os' to find files importing the os module, or 'TODO|FIXME' to find files containing TODO or FIXME comments. The pattern uses Python's re module syntax."
                        }
                    },
                    "additionalProperties": False,
                    "required": ["path", "pattern"]
                },
            },
        }


class FindLinesMatchingTool(LLMTool):
    def __init__(self, fs: FilesystemGateway):
        self.fs = fs

    def run(self, path: str, pattern: str) -> list[dict]:
        try:
            # Split the path into directory and filename
            directory, file_name = os.path.split(path)
            return self.fs.find_lines_matching(directory, file_name, pattern)
        except ValueError as e:
            return f"Error: {str(e)}"
        except FileNotFoundError:
            return f"Error: File '{path}' not found"
        except PermissionError:
            return f"Error: Permission denied when accessing file '{path}'"
        except re.error as e:
            return f"Error: Invalid regex pattern '{pattern}': {str(e)}"
        except IOError as e:
            return f"Error reading file '{path}': {str(e)}"
        except UnicodeDecodeError:
            return f"Error: File '{path}' contains non-text content that cannot be read as text"
        except Exception as e:
            return f"Error finding lines matching pattern '{pattern}' in file '{path}': {str(e)}"

    @property
    def descriptor(self):
        return {
            "type": "function",
            "function": {
                "name": "find_lines_matching",
                "description": "Find all lines in a file matching a regex pattern, returning both line numbers and content. Use this when you need to locate specific patterns within a single file and need to know exactly where they appear.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "The full relative path including the filename of the file to search in. For example, 'README.md' for a file in the root directory, 'src/main.py' for a file in the src directory, or 'docs/images/diagram.png' for a file in a nested directory."
                        },
                        "pattern": {
                            "type": "string",
                            "description": "The regex pattern to match lines against. Examples: 'def\\s+\\w+' to find all function definitions, 'class\\s+\\w+' to find all class definitions, or 'TODO|FIXME' to find all TODO or FIXME comments. The pattern uses Python's re module syntax."
                        }
                    },
                    "additionalProperties": False,
                    "required": ["path", "pattern"]
                },
            },
        }


class EditFileWithDiffTool(LLMTool):
    def __init__(self, fs: FilesystemGateway):
        self.fs = fs

    def run(self, path: str, diff: str) -> str:
        try:
            # Split the path into directory and filename
            directory, file_name = os.path.split(path)
            return self.fs.edit_file_with_diff(directory, file_name, diff)
        except ValueError as e:
            return f"Error: {str(e)}"
        except FileNotFoundError:
            return f"Error: File '{path}' not found"
        except PermissionError:
            return f"Error: Permission denied when accessing file '{path}'"
        except IOError as e:
            return f"Error accessing file '{path}': {str(e)}"
        except UnicodeDecodeError:
            return f"Error: File '{path}' contains non-text content that cannot be edited as text"
        except Exception as e:
            return f"Error applying diff to file '{path}': {str(e)}"

    @property
    def descriptor(self):
        return {
            "type": "function",
            "function": {
                "name": "edit_file_with_diff",
                "description": "Edit a file by applying a diff to it. Use this for making selective changes to parts of a file while preserving the rest of the content, unlike write_file which completely replaces the file. The diff should be in a unified diff format with lines prefixed by '+' (add), '-' (remove), or ' ' (context).",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "The full relative path including the filename of the file to edit. For example, 'README.md' for a file in the root directory, 'src/main.py' for a file in the src directory, or 'docs/images/diagram.png' for a file in a nested directory."
                        },
                        "diff": {
                            "type": "string",
                            "description": "The diff to apply to the file in unified diff format. Lines to add should be prefixed with '+', lines to remove with '-', and context lines with ' ' (space). Example:\n\n```\n This is a context line (unchanged)\n-This line will be removed\n+This line will be added\n This is another context line\n```\n\nThe diff should include enough context lines to uniquely identify the section of the file to modify."
                        }
                    },
                    "additionalProperties": False,
                    "required": ["path", "diff"]
                },
            },
        }


class CreateDirectoryTool(LLMTool):
    def __init__(self, fs: FilesystemGateway):
        self.fs = fs

    def run(self, path: str) -> str:
        try:
            # Resolve the path relative to the base path
            resolved_path = self.fs._resolve_path(path)

            # Create the directory
            os.makedirs(resolved_path, exist_ok=True)

            return f"Successfully created directory '{path}'"
        except ValueError as e:
            return f"Error: {str(e)}"
        except PermissionError:
            return f"Error: Permission denied when creating directory '{path}'"
        except OSError as e:
            return f"Error creating directory '{path}': {str(e)}"
        except Exception as e:
            return f"Error creating directory '{path}': {str(e)}"

    @property
    def descriptor(self):
        return {
            "type": "function",
            "function": {
                "name": "create_directory",
                "description": "Create a new directory at the specified path. If the directory already exists, this operation will succeed without error. Use this when you need to create a directory structure before writing files to it.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "The relative path where the directory should be created. For example, 'new_folder' for a directory in the root, 'src/new_folder' for a directory in the src directory, or 'docs/images/new_folder' for a nested directory. Parent directories will be created automatically if they don't exist."
                        }
                    },
                    "additionalProperties": False,
                    "required": ["path"]
                },
            },
        }
