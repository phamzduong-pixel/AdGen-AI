from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile


class StorageSizeLimitError(Exception):
    """Raised when an upload exceeds the configured storage limit."""


@dataclass(frozen=True)
class StoredFile:
    location: str
    size: int


class LocalFileStorage:
    """Local storage adapter that can later be replaced by cloud storage."""

    def __init__(self, root: Path):
        self.root = root.resolve()

    async def save(
        self,
        upload: UploadFile,
        extension: str,
        max_size: int,
        chunk_size: int,
    ) -> StoredFile:
        self.root.mkdir(parents=True, exist_ok=True)
        destination = self.root / f"{uuid4().hex}{extension}"
        size = 0

        try:
            with destination.open("xb") as output:
                while chunk := await upload.read(chunk_size):
                    size += len(chunk)
                    if size > max_size:
                        raise StorageSizeLimitError
                    output.write(chunk)
        except Exception:
            destination.unlink(missing_ok=True)
            raise

        return StoredFile(location=str(destination), size=size)

    def resolve(self, location: str) -> Path:
        stored_path = Path(location)
        if not stored_path.is_absolute():
            stored_path = self.root / stored_path
        stored_path = stored_path.resolve()
        try:
            stored_path.relative_to(self.root)
        except ValueError as error:
            raise FileNotFoundError("Stored file is outside the upload directory") from error
        if not stored_path.is_file():
            raise FileNotFoundError("Stored file does not exist")
        return stored_path

    def delete(self, location: str) -> None:
        try:
            self.resolve(location).unlink(missing_ok=True)
        except FileNotFoundError:
            return
