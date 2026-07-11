from __future__ import annotations

import logging
import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from fastapi import HTTPException, UploadFile

logger = logging.getLogger(__name__)

PDF_SIGNATURE = b"%PDF-"
UPLOAD_CHUNK_SIZE = 1024 * 1024
MAX_SAFE_FILENAME_LENGTH = 200


@dataclass(frozen=True)
class SavedUpload:
    filename: str
    file_path: Path
    file_size: int


def save_pdf_upload(
    file: UploadFile,
    upload_path: Path,
    max_bytes: int,
    *,
    reject_detail: str | None = "Only PDF files are supported.",
) -> SavedUpload:
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        detail = reject_detail or f"Only PDF files are supported. Rejected: {file.filename}"
        raise HTTPException(status_code=400, detail=detail)

    upload_path.mkdir(parents=True, exist_ok=True)
    safe_name = safe_pdf_filename(file.filename)
    file_path = upload_path / f"{uuid.uuid4()}_{safe_name}"

    try:
        file_size = _save_limited_upload(file, file_path, max_bytes)
        validate_pdf_signature(file_path)
    except HTTPException:
        delete_upload(file_path)
        raise
    except Exception as exc:
        delete_upload(file_path)
        raise HTTPException(status_code=400, detail="Failed to save uploaded PDF.") from exc
    finally:
        file.file.close()

    return SavedUpload(filename=safe_name, file_path=file_path, file_size=file_size)


def save_pdf_uploads(
    files: Sequence[UploadFile],
    upload_path: Path,
    per_file_max_bytes: int,
    total_max_bytes: int,
) -> list[SavedUpload]:
    saved_uploads: list[SavedUpload] = []
    total_size = 0
    try:
        for file in files:
            saved = save_pdf_upload(file, upload_path, per_file_max_bytes, reject_detail=None)
            saved_uploads.append(saved)
            total_size += saved.file_size
            if total_size > total_max_bytes:
                max_mb = total_max_bytes // (1024 * 1024)
                raise HTTPException(status_code=400, detail=f"Total batch size exceeds {max_mb} MB limit.")
    except Exception:
        for saved in saved_uploads:
            delete_upload(saved.file_path)
        raise
    return saved_uploads


def safe_pdf_filename(filename: str) -> str:
    safe_name = Path(filename).name
    if len(safe_name) <= MAX_SAFE_FILENAME_LENGTH:
        return safe_name

    suffix = Path(safe_name).suffix[:10]
    return safe_name[: MAX_SAFE_FILENAME_LENGTH - len(suffix)] + suffix


def validate_pdf_signature(file_path: Path) -> None:
    with file_path.open("rb") as saved_file:
        if saved_file.read(len(PDF_SIGNATURE)) != PDF_SIGNATURE:
            raise HTTPException(status_code=400, detail="Uploaded file is not a valid PDF.")


def delete_upload(file_path: Path) -> None:
    try:
        file_path.unlink(missing_ok=True)
    except OSError:
        logger.warning("Failed to remove partial upload %s", file_path, exc_info=True)


def _save_limited_upload(file: UploadFile, file_path: Path, max_bytes: int) -> int:
    total_size = 0
    with file_path.open("wb") as buffer:
        while True:
            chunk = file.file.read(UPLOAD_CHUNK_SIZE)
            if not chunk:
                break
            total_size += len(chunk)
            if total_size > max_bytes:
                max_mb = max_bytes // (1024 * 1024)
                raise HTTPException(status_code=400, detail=f"PDF file is too large. Maximum size is {max_mb} MB.")
            buffer.write(chunk)
    return total_size
