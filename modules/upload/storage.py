from pathlib import Path
from uuid import uuid4

from core.config import settings


class StorageService:
    """
    Handles local file storage.
    """

    UPLOAD_DIR = Path(settings.upload_dir)

    def __init__(self):
        self.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

    def save(self, filename: str, content: bytes):
        extension = Path(filename).suffix.lower()

        stored_filename = f"{uuid4()}{extension}"

        file_path = self.UPLOAD_DIR / stored_filename

        with open(file_path, "wb") as f:
            f.write(content)

        return stored_filename, str(file_path)
