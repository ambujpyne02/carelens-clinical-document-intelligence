"""Safe in-memory ingestion for supported clinical document inputs."""

from __future__ import annotations

import hashlib
from io import BytesIO
from pathlib import Path

from PIL import Image, UnidentifiedImageError
from pypdf import PdfReader

from .config import Settings
from .schemas import DocumentInput


ALLOWED_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg", ".txt"}
MIME_BY_EXTENSION = {
    ".pdf": "application/pdf",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".txt": "text/plain",
}


class IngestionError(ValueError):
    """Raised when an uploaded document is unsafe or outside demo limits."""


def _validate_pdf(content: bytes, settings: Settings) -> int:
    if not content.startswith(b"%PDF"):
        raise IngestionError("The file extension is PDF but the content is not a PDF.")
    try:
        reader = PdfReader(BytesIO(content))
        if reader.is_encrypted:
            try:
                unlocked = reader.decrypt("")
            except Exception as exc:  # pragma: no cover - library-specific
                raise IngestionError("Password-protected PDFs are not supported.") from exc
            if not unlocked:
                raise IngestionError("Password-protected PDFs are not supported.")
        page_count = len(reader.pages)
    except IngestionError:
        raise
    except Exception as exc:
        raise IngestionError("The PDF is damaged or cannot be read.") from exc
    if page_count < 1:
        raise IngestionError("The PDF has no readable pages.")
    if page_count > settings.max_pdf_pages:
        raise IngestionError(
            f"PDFs are limited to {settings.max_pdf_pages} pages for this demo."
        )
    return page_count


def _validate_image(content: bytes) -> None:
    try:
        with Image.open(BytesIO(content)) as image:
            image.verify()
        with Image.open(BytesIO(content)) as image:
            width, height = image.size
    except (UnidentifiedImageError, OSError) as exc:
        raise IngestionError("The image is damaged or uses an unsupported format.") from exc
    if width * height > 25_000_000:
        raise IngestionError("Images are limited to 25 megapixels for this demo.")


def make_document_input(
    filename: str,
    content: bytes,
    settings: Settings,
    mime_type: str | None = None,
) -> DocumentInput:
    safe_name = Path(filename).name
    extension = Path(safe_name).suffix.lower()
    if extension not in ALLOWED_EXTENSIONS:
        allowed = ", ".join(sorted(ALLOWED_EXTENSIONS))
        raise IngestionError(f"Unsupported file type. Allowed extensions: {allowed}.")
    if not content:
        raise IngestionError(f"{safe_name} is empty.")
    max_bytes = settings.max_file_mb * 1024 * 1024
    if len(content) > max_bytes:
        raise IngestionError(
            f"{safe_name} exceeds the {settings.max_file_mb} MB per-file limit."
        )

    expected_mime = MIME_BY_EXTENSION[extension]
    if mime_type and mime_type not in {
        expected_mime,
        "application/octet-stream",
        "image/jpg",
    }:
        raise IngestionError(
            f"{safe_name} has a MIME type that does not match its extension."
        )

    page_count: int | None = None
    if extension == ".pdf":
        page_count = _validate_pdf(content, settings)
    elif extension in {".png", ".jpg", ".jpeg"}:
        _validate_image(content)
        page_count = 1
    else:
        try:
            text = content.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise IngestionError("Text inputs must be valid UTF-8.") from exc
        if not text.strip():
            raise IngestionError(f"{safe_name} contains no readable text.")
        if len(text) > settings.max_text_chars:
            raise IngestionError(
                f"Text inputs are limited to {settings.max_text_chars:,} characters."
            )

    digest = hashlib.sha256(content).hexdigest()
    return DocumentInput(
        source_id=f"SRC-{digest[:8].upper()}",
        filename=safe_name,
        mime_type=expected_mime,
        size_bytes=len(content),
        sha256=digest,
        content=content,
        page_count=page_count,
    )


def validate_batch(
    documents: list[DocumentInput], settings: Settings
) -> tuple[list[DocumentInput], list[str]]:
    if not documents:
        raise IngestionError("Add at least one document or pasted text.")
    if len(documents) > settings.max_files:
        raise IngestionError(f"A case can include at most {settings.max_files} documents.")
    total_bytes = sum(document.size_bytes for document in documents)
    if total_bytes > settings.max_total_mb * 1024 * 1024:
        raise IngestionError(
            f"The combined upload is limited to {settings.max_total_mb} MB."
        )

    unique: list[DocumentInput] = []
    warnings: list[str] = []
    seen_hashes: set[str] = set()
    for document in documents:
        if document.sha256 in seen_hashes:
            warnings.append(f"Ignored duplicate document: {document.filename}.")
            continue
        seen_hashes.add(document.sha256)
        unique.append(document)
    if not unique:
        raise IngestionError("All supplied documents were duplicates.")
    return unique, warnings


def load_document(path: Path, settings: Settings) -> DocumentInput:
    return make_document_input(path.name, path.read_bytes(), settings)

