from pathlib import Path
from uuid import uuid4
from typing import Optional

from core.config import settings


class StorageService:
    """
    Handles local file storage and centralized run/document path generation.

    Storage layout:
        {STORAGE_DIR}/runs/{run_id}/documents/{document_id}/
            original/{original_filename}
            extracted/content.txt
            redacted/redacted.txt
            report.json

    Run and document directories are identified by their UUIDs only.
    Original filenames are preserved only inside the ``original`` directory
    and are sanitized to prevent path traversal.
    """

    STORAGE_DIR = Path(settings.storage_dir)
    RUNS_DIR = STORAGE_DIR / "runs"
    UPLOAD_DIR = Path(settings.upload_dir)

    def __init__(self):
        self.STORAGE_DIR.mkdir(parents=True, exist_ok=True)

    @classmethod
    def run_root(cls, run_id: str) -> Path:
        """Return the root directory for a run."""
        return cls.RUNS_DIR / run_id

    @classmethod
    def document_root(cls, run_id: str, document_id: str) -> Path:
        """Return the root directory for a document within a run."""
        return cls.run_root(run_id) / "documents" / document_id

    @classmethod
    def original_dir(cls, run_id: str, document_id: str) -> Path:
        """Return the directory holding the original uploaded file."""
        return cls.document_root(run_id, document_id) / "original"

    @classmethod
    def extracted_path(cls, run_id: str, document_id: str) -> Path:
        """Return the extracted text artifact path."""
        return cls.document_root(run_id, document_id) / "extracted" / "content.txt"

    @classmethod
    def redacted_path(cls, run_id: str, document_id: str) -> Path:
        """Return the redacted text artifact path."""
        return cls.document_root(run_id, document_id) / "redacted" / "redacted.txt"

    @classmethod
    def report_path(cls, run_id: str, document_id: str) -> Path:
        """Return the audit report artifact path."""
        return cls.document_root(run_id, document_id) / "report.json"

    @staticmethod
    def _sanitize_filename(filename: str) -> str:
        """
        Sanitize an original filename for safe storage.

        Strips any directory components to prevent path traversal and
        removes null bytes and unsafe characters.
        """
        if not filename:
            return "unnamed"

        normalized = filename.replace("\\", "/")
        name = Path(normalized).name
        name = "".join(
            char for char in name if char not in {"\x00", "/", "\\"}
        ).strip()

        if not name or name in {".", ".."}:
            return "unnamed"

        return name

    def save(
        self,
        filename: str,
        content: bytes,
        run_id: Optional[str] = None,
        document_id: Optional[str] = None,
    ) -> tuple:
        """
        Persist an uploaded file.

        When a run and document context is provided the file is stored in:
            {STORAGE_DIR}/runs/{run_id}/documents/{document_id}/original/{filename}

        Otherwise it is stored directly in the legacy upload directory.
        The returned ``stored_filename`` is always a unique identifier.

        Returns:
            Tuple of (stored_filename, file_path).
        """
        extension = Path(filename).suffix.lower()
        stored_filename = f"{uuid4()}{extension}"

        if run_id and document_id:
            base_path = self.original_dir(run_id, document_id)
            file_name = self._sanitize_filename(filename)
        else:
            base_path = self.UPLOAD_DIR
            file_name = stored_filename

        base_path.mkdir(parents=True, exist_ok=True)
        file_path = base_path / file_name

        with open(file_path, "wb") as f:
            f.write(content)

        return stored_filename, str(file_path)
