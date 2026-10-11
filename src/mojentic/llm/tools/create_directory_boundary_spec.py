import pytest

from mojentic.llm.tools.file_manager import CreateDirectoryTool, FilesystemGateway


class DescribeCreateDirectoryBoundary:
    def should_preserve_unexpected_path_failure_without_filesystem_mutation(
        self, tmp_path
    ):
        failure = RuntimeError("directory path conversion defect")

        class BrokenPath:
            def __fspath__(self):
                raise failure

        sentinel = tmp_path / "sentinel.txt"
        sentinel.write_bytes(b"unchanged")
        tool = CreateDirectoryTool(FilesystemGateway(str(tmp_path)))

        with pytest.raises(RuntimeError) as caught:
            tool.run(BrokenPath())

        assert caught.value is failure
        assert list(tmp_path.iterdir()) == [sentinel]
        assert sentinel.read_bytes() == b"unchanged"

    def should_create_nested_directories_and_accept_existing_directory(self, tmp_path):
        tool = CreateDirectoryTool(FilesystemGateway(str(tmp_path)))

        first = tool.run("nested/child")
        repeated = tool.run("nested/child")

        assert first == "Successfully created directory 'nested/child'"
        assert repeated == first
        assert (tmp_path / "nested/child").is_dir()

    def should_return_sandbox_error_without_creating_outside_directory(self, tmp_path):
        base = tmp_path / "sandbox"
        base.mkdir()
        tool = CreateDirectoryTool(FilesystemGateway(str(base)))

        result = tool.run("../outside")

        assert result == "Error: Path ../outside attempts to escape the sandbox"
        assert list(tmp_path.iterdir()) == [base]
        assert list(base.iterdir()) == []

    def should_return_os_error_without_replacing_existing_file(self, tmp_path):
        sentinel = tmp_path / "occupied"
        sentinel.write_bytes(b"unchanged")
        tool = CreateDirectoryTool(FilesystemGateway(str(tmp_path)))

        result = tool.run("occupied")

        assert result == (
            f"Error creating directory 'occupied': [Errno 17] File exists: '{sentinel}'"
        )
        assert list(tmp_path.iterdir()) == [sentinel]
        assert sentinel.read_bytes() == b"unchanged"

    def should_return_permission_error_from_path_boundary_without_mutation(
        self, tmp_path
    ):
        class DeniedPath:
            def __fspath__(self):
                raise PermissionError("path access denied")

            def __str__(self):
                return "denied"

        tool = CreateDirectoryTool(FilesystemGateway(str(tmp_path)))

        result = tool.run(DeniedPath())

        assert result == "Error: Permission denied when creating directory 'denied'"
        assert list(tmp_path.iterdir()) == []
