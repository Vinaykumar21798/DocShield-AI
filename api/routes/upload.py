from typing import Annotated, List

from fastapi import APIRouter, File, UploadFile, status

from api.dependencies import DatabaseSession
from modules.upload.service import UploadService

router = APIRouter(
    prefix="/upload",
    tags=["Upload"],
)


# ==========================================================
# Single File Upload
# ==========================================================

@router.post(
    "/",
    status_code=status.HTTP_201_CREATED,
    summary="Upload Document",
    description="Upload a single document.",
)
async def upload_document(
    file: UploadFile = File(...),
    db: DatabaseSession = None,
):
    """
    Upload a single document.
    """

    upload_service = UploadService(db)

    document = await upload_service.upload_single_document(file)

    return {
        "message": "Document uploaded successfully.",
        "document": {
            "document_id": document.id,
            "filename": document.filename,
            "status": document.status,
        },
    }


# ==========================================================
# Multiple File Upload
# ==========================================================

@router.post(
    "/bulk",
    status_code=status.HTTP_201_CREATED,
    summary="Upload Multiple Documents",
    description="Upload multiple documents.",
)
async def upload_documents(
    files: Annotated[
        List[UploadFile],
        File(
            description="",
            json_schema_extra={
                "type": "array",
                "items": {
                    "type": "string",
                    "format": "binary",
                },
            },
        ),
    ],
    db: DatabaseSession = None,
):
    """
    Upload multiple documents.
    """

    upload_service = UploadService(db)

    documents = await upload_service.upload_documents(files)

    return {
        "message": "Documents uploaded successfully.",
        "total_files": len(files),
        "uploaded": len(documents),
        "documents": [
            {
                "document_id": document.id,
                "filename": document.filename,
                "status": document.status,
            }
            for document in documents
        ],
    }