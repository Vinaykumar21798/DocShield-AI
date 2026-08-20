from pathlib import Path
from typing import Optional

from fastapi import HTTPException, status


def resolve_artifact_path(
    stored_path: Optional[str],
    allowed_root: str,
) -> Path:
    if not stored_path:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Artifact path is not available.",
        )

    requested_path = Path(stored_path)
    if not requested_path.is_absolute():
        requested_path = Path.cwd() / requested_path

    resolved_path = requested_path.resolve()
    root_path = (Path.cwd() / allowed_root).resolve()

    if resolved_path != root_path and root_path not in resolved_path.parents:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Artifact path is outside the allowed storage directory.",
        )

    relative_parts = {
        part.lower()
        for part in resolved_path.relative_to(root_path).parts
    }
    if relative_parts.intersection({"original", "extracted"}):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Requested path is not a generated artifact.",
        )

    if not resolved_path.exists() or not resolved_path.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Artifact file not found.",
        )

    return resolved_path
