import contextlib
import os
import types
import uuid
from typing import Optional

from fastapi import UploadFile

from app.core.config import settings


class TempFileManager:
    """
    Asynchronous context manager for handling temporary file uploads.

    Saves an incoming FastAPI UploadFile to settings.TEMP_STORAGE_PATH,
    returns its absolute path on entry, and ensures cleanup on exit.
    """

    def __init__(self, file: UploadFile) -> None:
        self.file = file
        self.file_path: Optional[str] = None

    async def __aenter__(self) -> str:
        # Ensure temporary storage directory exists
        os.makedirs(settings.TEMP_STORAGE_PATH, exist_ok=True)

        # Sanitize original filename to prevent path traversal
        raw_filename = self.file.filename or "document.docx"
        safe_filename = os.path.basename(raw_filename)
        unique_name = f"{uuid.uuid4().hex}_{safe_filename}"

        # Resolve absolute destination path
        abs_storage_dir = os.path.abspath(settings.TEMP_STORAGE_PATH)
        self.file_path = os.path.join(abs_storage_dir, unique_name)

        # Stream / write uploaded file content to disk
        await self.file.seek(0)
        with open(self.file_path, "wb") as destination:
            while chunk := await self.file.read(1024 * 1024):  # 1MB chunks
                destination.write(chunk)

        # Reset file position pointer for any potential subsequent use
        await self.file.seek(0)

        return self.file_path

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: types.TracebackType | None,
    ) -> None:
        if self.file_path:
            with contextlib.suppress(FileNotFoundError):
                os.remove(self.file_path)

