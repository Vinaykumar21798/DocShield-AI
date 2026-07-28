from pathlib import Path

from fastapi import HTTPException, UploadFile


class UploadValidator:
    """
    Validate uploaded files.
    """

    ALLOWED_EXTENSIONS = {
        ".pdf",
        ".png",
        ".jpg",
        ".jpeg",
        ".tiff",
        ".bmp",
        ".docx",
        ".txt",
    }

    MAX_FILE_SIZE = 20 * 1024 * 1024  # 20 MB

    @classmethod
    async def validate(cls, file: UploadFile) -> bytes:
        """
        Validate uploaded file and return file content.
        """

        if not file.filename:
            raise HTTPException(
                status_code=400,
                detail="Filename is missing.",
            )

        extension = Path(file.filename).suffix.lower()

        if extension not in cls.ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file type: {extension}",
            )

        contents = await file.read()

        if len(contents) == 0:
            raise HTTPException(
                status_code=400,
                detail="Uploaded file is empty.",
            )

        if len(contents) > cls.MAX_FILE_SIZE:
            raise HTTPException(
                status_code=400,
                detail="File exceeds maximum size (20 MB).",
            )

        return contents