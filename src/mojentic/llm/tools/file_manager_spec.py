import os
import re
import glob
import tempfile
import shutil
from unittest.mock import Mock, patch

import pytest

from mojentic.llm.tools.file_manager import (
    FilesystemGateway, FileManager, ListFilesTool, ReadFileTool, WriteFileTool,
    ListAllFilesTool, FindFilesByGlobTool, FindFilesContainingTool, FindLinesMatchingTool,
    EditFileWithDiffTool, CreateDirectoryTool
)


@pytest.fixture
def temp_dir():
    """Create a temporary directory for testing."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)


@pytest.fixture
def fs_gateway(temp_dir):
    """Create a FilesystemGateway with a temporary directory."""
    return FilesystemGateway(base_path=temp_dir)


@pytest.fixture
def file_manager(fs_gateway):
    """Create a FileManager with a filesystem gateway."""
    return FileManager(fs=fs_gateway)


@pytest.fixture
def setup_test_files(temp_dir):
    """Set up test files in the temporary directory."""
    # Create a directory structure
    os.makedirs(os.path.join(temp_dir, "subdir"), exist_ok=True)

    # Create test files
    with open(os.path.join(temp_dir, "test1.txt"), "w") as f:
        f.write("This is test file 1\nIt has multiple lines\nFor testing purposes")

    with open(os.path.join(temp_dir, "test2.py"), "w") as f:
        f.write("def test_function():\n    return 'Hello, World!'")

    with open(os.path.join(temp_dir, "subdir", "test3.txt"), "w") as f:
        f.write("This is a test file in a subdirectory")

    return temp_dir


class DescribeFilesystemGateway:

    def should_resolve_path_correctly(self, fs_gateway, temp_dir):
        """
        Given a FilesystemGateway
        When resolving a path
        Then it should correctly join with the base path
        """
        resolved_path = fs_gateway._resolve_path("test.txt")
        expected_path = os.path.normpath(os.path.join(temp_dir, "test.txt"))
        assert resolved_path == expected_path

    def should_prevent_path_traversal(self, fs_gateway):
        """
        Given a FilesystemGateway
        When resolving a path that attempts to escape the sandbox
        Then it should raise a ValueError
        """
        with pytest.raises(ValueError):
            fs_gateway._resolve_path("../../../etc/passwd")

    def should_list_files(self, fs_gateway, setup_test_files):
        """
        Given a FilesystemGateway with test files
        When listing files in the root directory
        Then it should return the correct list of files
        """
        files = fs_gateway.ls("")
        assert sorted(files) == sorted(["subdir", "test1.txt", "test2.py"])

    def should_list_all_files_recursively(self, fs_gateway, setup_test_files):
        """
        Given a FilesystemGateway with test files
        When listing all files recursively
        Then it should return all files including those in subdirectories
        """
        all_files = fs_gateway.list_all_files("")
        assert sorted(all_files) == sorted(["test1.txt", "test2.py", os.path.join("subdir", "test3.txt")])

    def should_find_files_by_glob(self, fs_gateway, setup_test_files):
        """
        Given a FilesystemGateway with test files
        When finding files by glob pattern
        Then it should return files matching the pattern
        """
        txt_files = fs_gateway.find_files_by_glob("", "*.txt")
        assert sorted(txt_files) == sorted(["test1.txt"])

        all_txt_files = fs_gateway.find_files_by_glob("", "**/*.txt")
        assert sorted(all_txt_files) == sorted(["test1.txt", os.path.join("subdir", "test3.txt")])

    def should_find_files_containing(self, fs_gateway, setup_test_files):
        """
        Given a FilesystemGateway with test files
        When finding files containing a pattern
        Then it should return files with content matching the pattern
        """
        files_with_hello = fs_gateway.find_files_containing("", "Hello")
        assert files_with_hello == ["test2.py"]

        files_with_test = fs_gateway.find_files_containing("", "test file")
        assert sorted(files_with_test) == sorted(["test1.txt", os.path.join("subdir", "test3.txt")])

    def should_find_lines_matching(self, fs_gateway, setup_test_files):
        """
        Given a FilesystemGateway with test files
        When finding lines matching a pattern in a file
        Then it should return the matching lines with line numbers
        """
        matching_lines = fs_gateway.find_lines_matching("", "test1.txt", "multiple")
        assert matching_lines == [{"line_number": 2, "content": "It has multiple lines"}]

    def should_edit_file_with_diff(self, fs_gateway, setup_test_files):
        """
        Given a FilesystemGateway with test files
        When editing a file with a diff
        Then it should apply the changes correctly
        """
        # Create a diff that changes "test file 1" to "modified file 1"
        diff = """--- test1.txt
+++ test1.txt
@@ -1,3 +1,3 @@
-This is test file 1
+This is modified file 1
 It has multiple lines
 For testing purposes"""

        result = fs_gateway.edit_file_with_diff("", "test1.txt", diff)
        assert "Successfully" in result

        # Verify the file was modified
        with open(os.path.join(setup_test_files, "test1.txt"), "r") as f:
            content = f.read()

        assert "This is modified file 1" in content
        assert "This is test file 1" not in content
        assert "It has multiple lines" in content
        assert "For testing purposes" in content

    def should_edit_file_with_diff_adding_lines(self, fs_gateway, setup_test_files):
        """
        Given a FilesystemGateway with test files
        When editing a file with a diff that adds lines
        Then it should add the lines while preserving the rest of the content
        """
        # Create a test file with known content
        test_file_path = os.path.join(setup_test_files, "add_lines_test.txt")
        with open(test_file_path, 'w') as f:
            f.write("Line 1\nLine 2\nLine 3\n")

        # Create a diff that adds a new line after Line 2
        diff = """--- add_lines_test.txt
+++ add_lines_test.txt
@@ -1,3 +1,4 @@
 Line 1
 Line 2
+New Line 2.5
 Line 3
"""

        result = fs_gateway.edit_file_with_diff("", "add_lines_test.txt", diff)
        assert "Successfully" in result

        # Verify the file was modified correctly
        with open(test_file_path, "r") as f:
            content = f.read()

        assert "Line 1\nLine 2\nNew Line 2.5\nLine 3\n" == content

    def should_edit_file_with_diff_removing_lines(self, fs_gateway, setup_test_files):
        """
        Given a FilesystemGateway with test files
        When editing a file with a diff that removes lines
        Then it should remove the lines while preserving the rest of the content
        """
        # Create a test file with known content
        test_file_path = os.path.join(setup_test_files, "remove_lines_test.txt")
        with open(test_file_path, 'w') as f:
            f.write("Line 1\nLine 2\nLine 3\nLine 4\n")

        # Create a diff that removes Line 3
        diff = """--- remove_lines_test.txt
+++ remove_lines_test.txt
@@ -1,4 +1,3 @@
 Line 1
 Line 2
-Line 3
 Line 4
"""

        result = fs_gateway.edit_file_with_diff("", "remove_lines_test.txt", diff)
        assert "Successfully" in result

        # Verify the file was modified correctly
        with open(test_file_path, "r") as f:
            content = f.read()

        assert "Line 1\nLine 2\nLine 4\n" == content

    def should_edit_file_with_diff_multiple_hunks(self, fs_gateway, setup_test_files):
        """
        Given a FilesystemGateway with test files
        When editing a file with a diff that contains multiple hunks
        Then it should apply all changes correctly
        """
        # Create a test file with known content
        test_file_path = os.path.join(setup_test_files, "multiple_hunks_test.txt")
        with open(test_file_path, 'w') as f:
            f.write("Line 1\nLine 2\nLine 3\nLine 4\nLine 5\nLine 6\n")

        # Create a diff with multiple hunks
        diff = """--- multiple_hunks_test.txt
+++ multiple_hunks_test.txt
@@ -1,3 +1,3 @@
 Line 1
-Line 2
+Modified Line 2
 Line 3
@@ -4,3 +4,4 @@
 Line 4
 Line 5
+New Line 5.5
 Line 6
"""

        result = fs_gateway.edit_file_with_diff("", "multiple_hunks_test.txt", diff)
        assert "Successfully" in result

        # Verify the file was modified correctly
        with open(test_file_path, "r") as f:
            content = f.read()

        expected = "Line 1\nModified Line 2\nLine 3\nLine 4\nLine 5\nNew Line 5.5\nLine 6\n"
        assert expected == content

    def should_read_file(self, fs_gateway, setup_test_files):
        """
        Given a FilesystemGateway with test files
        When reading a file
        Then it should return the file content
        """
        content = fs_gateway.read("", "test1.txt")
        assert "This is test file 1" in content

    def should_write_file(self, fs_gateway, setup_test_files):
        """
        Given a FilesystemGateway with test files
        When writing to a file
        Then it should update the file content
        """
        fs_gateway.write("", "new_file.txt", "This is a new file")

        # Verify the file was created
        with open(os.path.join(setup_test_files, "new_file.txt"), "r") as f:
            content = f.read()

        assert content == "This is a new file"


class DescribeFileManager:

    def should_list_files_with_extension(self, file_manager, setup_test_files):
        """
        Given a FileManager with test files
        When listing files with a specific extension
        Then it should return only files with that extension
        """
        txt_files = file_manager.ls("", ".txt")
        assert sorted(txt_files) == sorted(["test1.txt"])

    def should_list_all_files(self, file_manager, setup_test_files):
        """
        Given a FileManager with test files
        When listing all files
        Then it should return all files recursively
        """
        all_files = file_manager.list_all_files("")
        assert sorted(all_files) == sorted(["test1.txt", "test2.py", os.path.join("subdir", "test3.txt")])

    def should_find_files_by_glob(self, file_manager, setup_test_files):
        """
        Given a FileManager with test files
        When finding files by glob pattern
        Then it should return files matching the pattern
        """
        py_files = file_manager.find_files_by_glob("", "*.py")
        assert py_files == ["test2.py"]

    def should_find_files_containing(self, file_manager, setup_test_files):
        """
        Given a FileManager with test files
        When finding files containing a pattern
        Then it should return files with content matching the pattern
        """
        files_with_multiple = file_manager.find_files_containing("", "multiple")
        assert files_with_multiple == ["test1.txt"]

    def should_find_lines_matching(self, file_manager, setup_test_files):
        """
        Given a FileManager with test files
        When finding lines matching a pattern in a file
        Then it should return the matching lines with line numbers
        """
        matching_lines = file_manager.find_lines_matching("", "test1.txt", "testing")
        assert matching_lines == [{"line_number": 3, "content": "For testing purposes"}]

    def should_edit_file_with_diff(self, file_manager, setup_test_files):
        """
        Given a FileManager with test files
        When editing a file with a diff
        Then it should apply the changes correctly
        """
        # Create a diff that changes "test file 1" to "edited file 1"
        diff = """--- test1.txt
+++ test1.txt
@@ -1,3 +1,3 @@
-This is test file 1
+This is edited file 1
 It has multiple lines
 For testing purposes"""

        result = file_manager.edit_file_with_diff("", "test1.txt", diff)
        assert "Successfully" in result

        # Verify the file was modified
        content = file_manager.read("", "test1.txt")
        assert "This is edited file 1" in content

    def should_read_file(self, file_manager, setup_test_files):
        """
        Given a FileManager with test files
        When reading a file
        Then it should return the file content
        """
        content = file_manager.read("", "test2.py")
        assert "def test_function()" in content

    def should_write_file(self, file_manager, setup_test_files):
        """
        Given a FileManager with test files
        When writing to a file
        Then it should update the file content
        """
        file_manager.write("", "new_file2.txt", "This is another new file")

        # Verify the file was created
        content = file_manager.read("", "new_file2.txt")
        assert content == "This is another new file"


class DescribeListFilesTool:

    def should_list_files_with_extension(self, setup_test_files):
        """
        Given a ListFilesTool
        When running with an extension
        Then it should return files with that extension
        """
        fs = FilesystemGateway(base_path=setup_test_files)
        tool = ListFilesTool(fs)
        result = tool.run(path="", extension=".txt")
        assert sorted(result) == sorted(["test1.txt"])

    def should_have_correct_descriptor(self):
        """
        Given a ListFilesTool
        When accessing its descriptor
        Then it should have the correct structure
        """
        fs = FilesystemGateway(base_path="/tmp")
        tool = ListFilesTool(fs)
        descriptor = tool.descriptor
        assert descriptor["type"] == "function"
        assert descriptor["function"]["name"] == "list_files"
        assert "path" in descriptor["function"]["parameters"]["properties"]
        assert "extension" in descriptor["function"]["parameters"]["properties"]


class DescribeReadFileTool:

    def should_read_file_content(self, setup_test_files):
        """
        Given a ReadFileTool
        When running with a path
        Then it should return the file content
        """
        fs = FilesystemGateway(base_path=setup_test_files)
        tool = ReadFileTool(fs)
        result = tool.run(path="test1.txt")
        assert "This is test file 1" in result

    def should_have_correct_descriptor(self):
        """
        Given a ReadFileTool
        When accessing its descriptor
        Then it should have the correct structure
        """
        fs = FilesystemGateway(base_path="/tmp")
        tool = ReadFileTool(fs)
        descriptor = tool.descriptor
        assert descriptor["type"] == "function"
        assert descriptor["function"]["name"] == "read_file"
        assert "path" in descriptor["function"]["parameters"]["properties"]
        assert "file_name" not in descriptor["function"]["parameters"]["properties"]


class DescribeWriteFileTool:

    def should_write_file_content(self, setup_test_files):
        """
        Given a WriteFileTool
        When running with a path and content
        Then it should write the content to the file
        """
        fs = FilesystemGateway(base_path=setup_test_files)
        tool = WriteFileTool(fs)
        result = tool.run(path="write_test.txt", content="Test content")
        assert "Successfully" in result

        # Verify the file was created
        with open(os.path.join(setup_test_files, "write_test.txt"), "r") as f:
            content = f.read()
        assert content == "Test content"

    def should_have_correct_descriptor(self):
        """
        Given a WriteFileTool
        When accessing its descriptor
        Then it should have the correct structure
        """
        fs = FilesystemGateway(base_path="/tmp")
        tool = WriteFileTool(fs)
        descriptor = tool.descriptor
        assert descriptor["type"] == "function"
        assert descriptor["function"]["name"] == "write_file"
        assert "path" in descriptor["function"]["parameters"]["properties"]
        assert "content" in descriptor["function"]["parameters"]["properties"]
        assert "file_name" not in descriptor["function"]["parameters"]["properties"]


class DescribeListAllFilesTool:

    def should_list_all_files(self, setup_test_files):
        """
        Given a ListAllFilesTool
        When running
        Then it should return all files recursively
        """
        fs = FilesystemGateway(base_path=setup_test_files)
        tool = ListAllFilesTool(fs)
        result = tool.run(path="")
        assert sorted(result) == sorted(["test1.txt", "test2.py", os.path.join("subdir", "test3.txt")])

    def should_have_correct_descriptor(self):
        """
        Given a ListAllFilesTool
        When accessing its descriptor
        Then it should have the correct structure
        """
        fs = FilesystemGateway(base_path="/tmp")
        tool = ListAllFilesTool(fs)
        descriptor = tool.descriptor
        assert descriptor["type"] == "function"
        assert descriptor["function"]["name"] == "list_all_files"
        assert "path" in descriptor["function"]["parameters"]["properties"]


class DescribeFindFilesByGlobTool:

    def should_find_files_by_glob_pattern(self, setup_test_files):
        """
        Given a FindFilesByGlobTool
        When running with a glob pattern
        Then it should return files matching the pattern
        """
        fs = FilesystemGateway(base_path=setup_test_files)
        tool = FindFilesByGlobTool(fs)
        result = tool.run(path="", pattern="*.py")
        assert result == ["test2.py"]

    def should_have_correct_descriptor(self):
        """
        Given a FindFilesByGlobTool
        When accessing its descriptor
        Then it should have the correct structure
        """
        fs = FilesystemGateway(base_path="/tmp")
        tool = FindFilesByGlobTool(fs)
        descriptor = tool.descriptor
        assert descriptor["type"] == "function"
        assert descriptor["function"]["name"] == "find_files_by_glob"
        assert "path" in descriptor["function"]["parameters"]["properties"]
        assert "pattern" in descriptor["function"]["parameters"]["properties"]


class DescribeFindFilesContainingTool:

    def should_find_files_containing_pattern(self, setup_test_files):
        """
        Given a FindFilesContainingTool
        When running with a regex pattern
        Then it should return files containing text matching the pattern
        """
        fs = FilesystemGateway(base_path=setup_test_files)
        tool = FindFilesContainingTool(fs)
        result = tool.run(path="", pattern="Hello")
        assert result == ["test2.py"]

    def should_have_correct_descriptor(self):
        """
        Given a FindFilesContainingTool
        When accessing its descriptor
        Then it should have the correct structure
        """
        fs = FilesystemGateway(base_path="/tmp")
        tool = FindFilesContainingTool(fs)
        descriptor = tool.descriptor
        assert descriptor["type"] == "function"
        assert descriptor["function"]["name"] == "find_files_containing"
        assert "path" in descriptor["function"]["parameters"]["properties"]
        assert "pattern" in descriptor["function"]["parameters"]["properties"]


class DescribeFindLinesMatchingTool:

    def should_find_lines_matching_pattern(self, setup_test_files):
        """
        Given a FindLinesMatchingTool
        When running with a path and regex pattern
        Then it should return lines matching the pattern with line numbers
        """
        fs = FilesystemGateway(base_path=setup_test_files)
        tool = FindLinesMatchingTool(fs)
        result = tool.run(path="test1.txt", pattern="multiple")
        assert result == [{"line_number": 2, "content": "It has multiple lines"}]

    def should_have_correct_descriptor(self):
        """
        Given a FindLinesMatchingTool
        When accessing its descriptor
        Then it should have the correct structure
        """
        fs = FilesystemGateway(base_path="/tmp")
        tool = FindLinesMatchingTool(fs)
        descriptor = tool.descriptor
        assert descriptor["type"] == "function"
        assert descriptor["function"]["name"] == "find_lines_matching"
        assert "path" in descriptor["function"]["parameters"]["properties"]
        assert "file_name" not in descriptor["function"]["parameters"]["properties"]
        assert "pattern" in descriptor["function"]["parameters"]["properties"]


class DescribeEditFileWithDiffTool:

    def should_edit_file_with_diff(self, setup_test_files):
        """
        Given an EditFileWithDiffTool
        When running with a path and diff
        Then it should apply the diff to the file
        """
        fs = FilesystemGateway(base_path=setup_test_files)
        tool = EditFileWithDiffTool(fs)

        # Create a diff that changes "test file 1" to "modified by tool"
        diff = """--- test1.txt
+++ test1.txt
@@ -1,3 +1,3 @@
-This is test file 1
+This is modified by tool
 It has multiple lines
 For testing purposes"""

        result = tool.run(path="test1.txt", diff=diff)
        assert "Successfully" in result

        # Verify the file was modified
        with open(os.path.join(setup_test_files, "test1.txt"), "r") as f:
            content = f.read()
        assert "This is modified by tool" in content
        assert "This is test file 1" not in content
        assert "It has multiple lines" in content
        assert "For testing purposes" in content

    def should_edit_file_with_diff_adding_lines(self, setup_test_files):
        """
        Given an EditFileWithDiffTool
        When running with a path and diff that adds lines
        Then it should add the lines while preserving the rest of the content
        """
        fs = FilesystemGateway(base_path=setup_test_files)
        tool = EditFileWithDiffTool(fs)

        # Create a test file with known content
        test_file_path = os.path.join(setup_test_files, "tool_add_lines_test.txt")
        with open(test_file_path, 'w') as f:
            f.write("Line 1\nLine 2\nLine 3\n")

        # Create a diff that adds a new line after Line 2
        diff = """--- tool_add_lines_test.txt
+++ tool_add_lines_test.txt
@@ -1,3 +1,4 @@
 Line 1
 Line 2
+New Line 2.5
 Line 3
"""

        result = tool.run(path="tool_add_lines_test.txt", diff=diff)
        assert "Successfully" in result

        # Verify the file was modified correctly
        with open(test_file_path, "r") as f:
            content = f.read()

        assert "Line 1\nLine 2\nNew Line 2.5\nLine 3\n" == content

    def should_edit_file_with_diff_multiple_hunks(self, setup_test_files):
        """
        Given an EditFileWithDiffTool
        When running with a path and diff that contains multiple hunks
        Then it should apply all changes correctly
        """
        fs = FilesystemGateway(base_path=setup_test_files)
        tool = EditFileWithDiffTool(fs)

        # Create a test file with known content
        test_file_path = os.path.join(setup_test_files, "tool_multiple_hunks_test.txt")
        with open(test_file_path, 'w') as f:
            f.write("Line 1\nLine 2\nLine 3\nLine 4\nLine 5\nLine 6\n")

        # Create a diff with multiple hunks
        diff = """--- tool_multiple_hunks_test.txt
+++ tool_multiple_hunks_test.txt
@@ -1,3 +1,3 @@
 Line 1
-Line 2
+Modified Line 2
 Line 3
@@ -4,3 +4,4 @@
 Line 4
 Line 5
+New Line 5.5
 Line 6
"""

        result = tool.run(path="tool_multiple_hunks_test.txt", diff=diff)
        assert "Successfully" in result

        # Verify the file was modified correctly
        with open(test_file_path, "r") as f:
            content = f.read()

        expected = "Line 1\nModified Line 2\nLine 3\nLine 4\nLine 5\nNew Line 5.5\nLine 6\n"
        assert expected == content

    def should_have_correct_descriptor(self):
        """
        Given an EditFileWithDiffTool
        When accessing its descriptor
        Then it should have the correct structure
        """
        fs = FilesystemGateway(base_path="/tmp")
        tool = EditFileWithDiffTool(fs)
        descriptor = tool.descriptor
        assert descriptor["type"] == "function"
        assert descriptor["function"]["name"] == "edit_file_with_diff"
        assert "path" in descriptor["function"]["parameters"]["properties"]
        assert "file_name" not in descriptor["function"]["parameters"]["properties"]
        assert "diff" in descriptor["function"]["parameters"]["properties"]


class DescribeCreateDirectoryTool:

    def should_create_directory(self, setup_test_files):
        """
        Given a CreateDirectoryTool
        When running with a path
        Then it should create the directory
        """
        fs = FilesystemGateway(base_path=setup_test_files)
        tool = CreateDirectoryTool(fs)

        # Create a new directory
        result = tool.run(path="new_directory")
        assert "Successfully" in result

        # Verify the directory was created
        assert os.path.isdir(os.path.join(setup_test_files, "new_directory"))

        # Test creating nested directories
        result = tool.run(path="nested/directory/structure")
        assert "Successfully" in result

        # Verify the nested directories were created
        assert os.path.isdir(os.path.join(setup_test_files, "nested/directory/structure"))

    def should_have_correct_descriptor(self):
        """
        Given a CreateDirectoryTool
        When accessing its descriptor
        Then it should have the correct structure
        """
        fs = FilesystemGateway(base_path="/tmp")
        tool = CreateDirectoryTool(fs)
        descriptor = tool.descriptor
        assert descriptor["type"] == "function"
        assert descriptor["function"]["name"] == "create_directory"
        assert "path" in descriptor["function"]["parameters"]["properties"]
