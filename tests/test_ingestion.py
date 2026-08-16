from __future__ import annotations

from io import BytesIO

import pytest
from PIL import Image
from pypdf import PdfWriter

from carelens.config import Settings
from carelens.ingestion import IngestionError, make_document_input, validate_batch


SETTINGS = Settings(openai_api_key="test")


def _pdf_bytes() -> bytes:
    writer = PdfWriter()
    writer.add_blank_page(width=612, height=792)
    stream = BytesIO()
    writer.write(stream)
    return stream.getvalue()


def _png_bytes() -> bytes:
    stream = BytesIO()
    Image.new("RGB", (100, 100), "white").save(stream, "PNG")
    return stream.getvalue()


@pytest.mark.parametrize(
    ("filename", "content", "mime", "pages"),
    [
        ("sample.pdf", _pdf_bytes(), "application/pdf", 1),
        ("sample.png", _png_bytes(), "image/png", 1),
        ("sample.txt", b"synthetic note", "text/plain", None),
    ],
)
def test_supported_inputs(filename, content, mime, pages):
    document = make_document_input(filename, content, SETTINGS, mime)
    assert document.page_count == pages
    assert document.source_id.startswith("SRC-")


@pytest.mark.parametrize(
    ("filename", "content", "mime"),
    [
        ("sample.exe", b"x", "application/octet-stream"),
        ("fake.pdf", b"not a pdf", "application/pdf"),
        ("bad.txt", b"\xff\xfe", "text/plain"),
        ("empty.txt", b"  \n", "text/plain"),
        ("sample.png", _png_bytes(), "application/pdf"),
    ],
)
def test_rejects_invalid_inputs(filename, content, mime):
    with pytest.raises(IngestionError):
        make_document_input(filename, content, SETTINGS, mime)


def test_batch_deduplicates_and_warns():
    first = make_document_input("one.txt", b"same", SETTINGS)
    second = make_document_input("two.txt", b"same", SETTINGS)
    documents, warnings = validate_batch([first, second], SETTINGS)
    assert len(documents) == 1
    assert "duplicate" in warnings[0].lower()

