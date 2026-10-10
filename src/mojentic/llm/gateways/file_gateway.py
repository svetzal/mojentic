from pathlib import Path


class FileGateway:
    def read(self, path: Path | str):
        if isinstance(path, str):
            path = Path(path)
        with open(path, "r") as file:
            return file.read()

    def exists(self, path: Path | str) -> bool:
        """
        Check if a file exists.

        Parameters
        ----------
        path : Union[Path, str]
            Path to the file

        Returns
        -------
        bool
            True if the file exists, False otherwise
        """
        if isinstance(path, str):
            path = Path(path)
        return path.exists()

    def is_binary(self, path: Path | str) -> bool:
        """
        Check if a file is binary.

        Parameters
        ----------
        path : Union[Path, str]
            Path to the file

        Returns
        -------
        bool
            True if the file is binary, False otherwise
        """
        if isinstance(path, str):
            path = Path(path)
        try:
            with open(path, "rb") as file:
                # Read the first 1024 bytes
                chunk = file.read(1024)
                # Check for null bytes, which are typically present in binary files
                return b"\0" in chunk
        except OSError:
            # If there's an error reading the file, assume it's binary
            return True
