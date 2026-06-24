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
ALLOWED_MATERIAL_EXTENSIONS = {".jpg", ".jpeg", ".png", ".pdf", ".pptx", ".mp4"}
ALLOWED_MATERIAL_MIME_TYPES = {
    "image/jpeg",
    "image/png",
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    "video/mp4",
}
FILE_SIGNATURES: list[tuple[bytes, str]] = [
    (b"\xff\xd8\xff", "image/jpeg"),
    (b"\x89PNG\r\n\x1a\n", "image/png"),
    (b"%PDF", "application/pdf"),
    (b"PK\x03\x04", "application/vnd.openxmlformats-officedocument.presentationml.presentation"),
]
MATERIAL_SIGNATURES: list[tuple[bytes, str]] = [
    *FILE_SIGNATURES,
    (b"\x00\x00\x00", "video/mp4"),
]


def _detect_mime(header: bytes) -> str | None:
    for signature, mime in FILE_SIGNATURES:
        if header.startswith(signature):
            return mime
    return None


def _detect_material_mime(header: bytes) -> str | None:
    if len(header) >= 12 and header[4:8] == b"ftyp":
        return "video/mp4"
    for signature, mime in MATERIAL_SIGNATURES:
        if mime == "video/mp4":
            continue
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


async def save_material_file(*, upload: UploadFile) -> str:
    if not upload.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Имя файла не указано",
        )

    ext = _normalize_extension(upload.filename)
    if ext not in ALLOWED_MATERIAL_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Допустимые форматы: JPG, PNG, PDF, PPTX, MP4",
        )

    content_type = (upload.content_type or "").split(";")[0].strip().lower()
    if content_type and content_type not in ALLOWED_MATERIAL_MIME_TYPES:
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
    if len(content) > settings.material_max_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Размер файла не должен превышать {settings.material_max_mb} МБ",
        )

    detected_mime = _detect_material_mime(content[:32])
    if detected_mime is None or detected_mime not in ALLOWED_MATERIAL_MIME_TYPES:
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
    target_dir = Path(settings.upload_dir) / "materials"
    target_dir.mkdir(parents=True, exist_ok=True)

    stored_name = f"{uuid.uuid4()}{storage_ext}"
    target_path = target_dir / stored_name
    target_path.write_bytes(content)

    return str(Path("materials") / stored_name).replace("\\", "/")


ALLOWED_TASK_COVER_EXTENSIONS = {".jpg", ".jpeg", ".png"}
TASK_COVER_MAX_BYTES = 5 * 1024 * 1024


async def save_task_cover_image(*, upload: UploadFile) -> str:
    if not upload.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Имя файла не указано",
        )

    ext = _normalize_extension(upload.filename)
    if ext not in ALLOWED_TASK_COVER_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Обложка задания: допустимы только JPG и PNG",
        )

    content_type = (upload.content_type or "").split(";")[0].strip().lower()
    allowed_mimes = {"image/jpeg", "image/png"}
    if content_type and content_type not in allowed_mimes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Недопустимый тип файла обложки",
        )

    content = await upload.read()
    if not content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Файл пустой",
        )
    if len(content) > TASK_COVER_MAX_BYTES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Размер обложки не должен превышать 5 МБ",
        )

    detected_mime = _detect_mime(content[:16])
    if detected_mime is None or detected_mime not in allowed_mimes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Содержимое файла не соответствует допустимому формату",
        )

    storage_ext = ".jpg" if ext in {".jpg", ".jpeg"} else ext
    target_dir = Path(settings.upload_dir) / "tasks" / "covers"
    target_dir.mkdir(parents=True, exist_ok=True)

    stored_name = f"{uuid.uuid4()}{storage_ext}"
    target_path = target_dir / stored_name
    target_path.write_bytes(content)

    return str(Path("tasks") / "covers" / stored_name).replace("\\", "/")


ALLOWED_PRIZE_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
PRIZE_IMAGE_MAX_BYTES = 5 * 1024 * 1024
PRIZE_IMAGE_MIMES = {
    "image/jpeg",
    "image/png",
    "image/webp",
    "image/gif",
}


def _detect_prize_image_mime(header: bytes) -> str | None:
    if header.startswith(b"GIF87a") or header.startswith(b"GIF89a"):
        return "image/gif"
    if header.startswith(b"RIFF") and len(header) >= 12 and header[8:12] == b"WEBP":
        return "image/webp"
    return _detect_mime(header)


async def save_prize_image(*, upload: UploadFile) -> str:
    if not upload.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Имя файла не указано",
        )

    ext = _normalize_extension(upload.filename)
    if ext == ".webp":
        storage_ext = ".webp"
    elif ext == ".gif":
        storage_ext = ".gif"
    elif ext not in ALLOWED_PRIZE_IMAGE_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Допустимые форматы: JPG, PNG, WEBP, GIF",
        )

    content_type = (upload.content_type or "").split(";")[0].strip().lower()
    if content_type and content_type not in PRIZE_IMAGE_MIMES:
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
    if len(content) > PRIZE_IMAGE_MAX_BYTES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Размер изображения не должен превышать 5 МБ",
        )

    detected_mime = _detect_prize_image_mime(content[:16])
    if detected_mime is None or detected_mime not in PRIZE_IMAGE_MIMES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Содержимое файла не соответствует допустимому формату",
        )

    if ext in {".jpg", ".jpeg"}:
        storage_ext = ".jpg"
    elif ext == ".png":
        storage_ext = ".png"

    target_dir = Path(settings.upload_dir) / "prizes"
    target_dir.mkdir(parents=True, exist_ok=True)

    stored_name = f"{uuid.uuid4()}{storage_ext}"
    target_path = target_dir / stored_name
    target_path.write_bytes(content)

    return str(Path("prizes") / stored_name).replace("\\", "/")


async def save_instruction_file(*, upload: UploadFile) -> tuple[str, str]:
    """Returns (file_path, content_type) where content_type is pdf or image."""
    if not upload.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Имя файла не указано",
        )

    ext = _normalize_extension(upload.filename)
    if ext not in {".jpg", ".jpeg", ".png", ".webp", ".gif", ".pdf"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Допустимые форматы: JPG, PNG, WEBP, GIF, PDF",
        )

    allowed_mimes = {
        *PRIZE_IMAGE_MIMES,
        "application/pdf",
    }
    content_type = (upload.content_type or "").split(";")[0].strip().lower()
    if content_type and content_type not in allowed_mimes:
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
    max_bytes = settings.material_max_bytes
    if len(content) > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Размер файла не должен превышать {settings.material_max_mb} МБ",
        )

    if ext == ".pdf":
        detected = _detect_mime(content[:16])
        if detected != "application/pdf":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Файл не является PDF",
            )
        storage_ext = ".pdf"
        logical_type = "pdf"
    else:
        detected = _detect_prize_image_mime(content[:16])
        if detected is None or detected not in PRIZE_IMAGE_MIMES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Содержимое файла не соответствует допустимому формату",
            )
        if ext in {".jpg", ".jpeg"}:
            storage_ext = ".jpg"
        elif ext == ".webp":
            storage_ext = ".webp"
        elif ext == ".gif":
            storage_ext = ".gif"
        else:
            storage_ext = ".png"
        logical_type = "image"

    target_dir = Path(settings.upload_dir) / "instructions"
    target_dir.mkdir(parents=True, exist_ok=True)

    stored_name = f"{uuid.uuid4()}{storage_ext}"
    target_path = target_dir / stored_name
    target_path.write_bytes(content)

    return str(Path("instructions") / stored_name).replace("\\", "/"), logical_type


async def save_legal_file(*, upload: UploadFile) -> tuple[str, str]:
    """Returns (file_path, content_type) where content_type is pdf or image."""
    if not upload.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Имя файла не указано",
        )

    ext = _normalize_extension(upload.filename)
    if ext not in {".jpg", ".jpeg", ".png", ".webp", ".gif", ".pdf"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Допустимые форматы: JPG, PNG, WEBP, GIF, PDF",
        )

    allowed_mimes = {
        *PRIZE_IMAGE_MIMES,
        "application/pdf",
    }
    content_type = (upload.content_type or "").split(";")[0].strip().lower()
    if content_type and content_type not in allowed_mimes:
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
    max_bytes = settings.material_max_bytes
    if len(content) > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Размер файла не должен превышать {settings.material_max_mb} МБ",
        )

    if ext == ".pdf":
        detected = _detect_mime(content[:16])
        if detected != "application/pdf":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Файл не является PDF",
            )
        storage_ext = ".pdf"
        logical_type = "pdf"
    else:
        detected = _detect_prize_image_mime(content[:16])
        if detected is None or detected not in PRIZE_IMAGE_MIMES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Содержимое файла не соответствует допустимому формату",
            )
        if ext in {".jpg", ".jpeg"}:
            storage_ext = ".jpg"
        elif ext == ".webp":
            storage_ext = ".webp"
        elif ext == ".gif":
            storage_ext = ".gif"
        else:
            storage_ext = ".png"
        logical_type = "image"

    target_dir = Path(settings.upload_dir) / "legal"
    target_dir.mkdir(parents=True, exist_ok=True)

    stored_name = f"{uuid.uuid4()}{storage_ext}"
    target_path = target_dir / stored_name
    target_path.write_bytes(content)

    return str(Path("legal") / stored_name).replace("\\", "/"), logical_type
