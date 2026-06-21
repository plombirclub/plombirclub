import uuid
from pathlib import Path

from fastapi import HTTPException, UploadFile, status

from app.core.config import settings

ALLOWED_DOCUMENT_EXTENSIONS = {".jpg", ".jpeg", ".png", ".pdf"}
ALLOWED_DOCUMENT_MIME_TYPES = {
    "image/jpeg",
    "image/png",
    "application/pdf",
}
FILE_SIGNATURES: list[tuple[bytes, str]] = [
    (b"\xff\xd8\xff", "image/jpeg"),
    (b"\x89PNG\r\n\x1a\n", "image/png"),
    (b"%PDF", "application/pdf"),
]


def _detect_mime(header: bytes) -> str | None:
    for signature, mime in FILE_SIGNATURES:
        if header.startswith(signature):
            return mime
    return None


def _normalize_extension(filename: str) -> str:
    ext = Path(filename).suffix.lower()
    if ext == ".jpeg":
        return ".jpg"
    return ext


async def save_user_document(*, upload: UploadFile, subdirectory: str) -> str:
    if not upload.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Имя файла не указано",
        )

    ext = _normalize_extension(upload.filename)
    if ext not in ALLOWED_DOCUMENT_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Допустимые форматы: JPG, PNG, PDF",
        )

    content_type = (upload.content_type or "").split(";")[0].strip().lower()
    if content_type and content_type not in ALLOWED_DOCUMENT_MIME_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Недопустимый тип файла",
        )

    content = await upload.read()
    if not content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Файл пустой",
        )
    if len(content) > settings.user_document_max_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Размер файла не должен превышать {settings.user_document_max_mb} МБ",
        )

    detected_mime = _detect_mime(content[:16])
    if detected_mime is None or detected_mime not in ALLOWED_DOCUMENT_MIME_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Содержимое файла не соответствует допустимому формату",
        )
    if content_type and content_type != detected_mime:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="MIME-тип не совпадает с содержимым файла",
        )

    storage_ext = ".jpg" if ext in {".jpg", ".jpeg"} else ext
    target_dir = Path(settings.upload_dir) / subdirectory
    target_dir.mkdir(parents=True, exist_ok=True)

    stored_name = f"{uuid.uuid4()}{storage_ext}"
    target_path = target_dir / stored_name
    target_path.write_bytes(content)

    return str(Path(subdirectory) / stored_name).replace("\\", "/")
