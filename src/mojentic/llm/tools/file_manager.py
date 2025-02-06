import os

from mojentic.llm.tools.llm_tool import LLMTool


class FilesystemGateway:
    def ls(self, path):
        return os.listdir(path)

    def read(self, path, file_name):
        with open(os.path.join(path, file_name), 'r') as f:
            return f.read()

    def write(self, path, file_name, content):
        with open(os.path.join(path, file_name), 'w') as f:
            f.write(content)


class FileManager:
    def __init__(self, path: str, fs=None):
        self.path: str = path
        self.fs = fs or FilesystemGateway()

    def ls(self, extension):
        entries = self.fs.ls(self.path)
        return [f for f in entries if f.endswith(extension)]

    def read(self, file_name):
        return self.fs.read(self.path, file_name)

    def write(self, file_name, content):
        self.fs.write(self.path, file_name, content)


class ListFilesTool(FileManager):
    def run(self, extension):
        entries = self.fs.ls(self.path)
        return [f for f in entries if f.endswith(extension)]

    @property
    def descriptor(self):
        return {
            "type": "function",
            "function": {
                "name": "list_files",
                "description": "List files in a directory with a specific extension.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "extension": {
                            "type": "string",
                            "description": "The file extension to filter by."
                        }
                    },
                    "additionalProperties": False,
                    "required": ["extension"]
                },
            },
        }


class ReadFileTool(LLMTool):
    def __init__(self, path: str, fs=None):
        self.path: str = path
        self.fs = fs or FilesystemGateway()

    def run(self, file_name):
        return self.fs.read(self.path, file_name)

    @property
    def descriptor(self):
        return {
            "type": "function",
            "function": {
                "name": "read_file",
                "description": "Read the content of a file.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "file_name": {
                            "type": "string",
                            "description": "The name of the file to read."
                        }
                    },
                    "additionalProperties": False,
                    "required": ["file_name"]
                },
            },
        }


class WriteFileTool(LLMTool):
    def __init__(self, path: str, fs=None):
        self.path: str = path
        self.fs = fs or FilesystemGateway()

    def run(self, file_name, content):
        self.fs.write(self.path, file_name, content)
        return f"Successfully wrote to {file_name}"

    @property
    def descriptor(self):
        return {
            "type": "function",
            "function": {
                "name": "write_file",
                "description": "Write content to a file.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "file_name": {
                            "type": "string",
                            "description": "The name of the file to write to."
                        },
                        "content": {
                            "type": "string",
                            "description": "The content to write to the file."
                        }
                    },
                    "additionalProperties": False,
                    "required": ["file_name", "content"]
                },
            },
        }
