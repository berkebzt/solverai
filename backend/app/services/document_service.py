import os
import re
from typing import Tuple
from fastapi import UploadFile
from config import settings


class DocumentService:
    """Handles document storage on disk."""

    def __init__(self):
        self.storage_dir = settings.absolute_documents_dir
        os.makedirs(self.storage_dir, exist_ok=True)

    def _sanitize_filename(self, filename: str) -> str:
        return re.sub(r"[^A-Za-z0-9._-]", "_", filename)

    def build_stored_filename(self, document_id: str, original_name: str) -> str:
        safe_name = self._sanitize_filename(original_name)
        return f"{document_id}_{safe_name}"

    async def save_upload(self, file: UploadFile, stored_filename: str) -> Tuple[str, int]:
        """Persist upload to disk and return (path, size)."""
        storage_path = os.path.join(self.storage_dir, stored_filename)

        content = await file.read()
        with open(storage_path, "wb") as f:
            f.write(content)

        return storage_path, len(content)

    def remove_file(self, path: str):
        if path and os.path.exists(path):
            os.remove(path)


document_service = DocumentService()

