from __future__ import annotations

from io import BytesIO
from types import SimpleNamespace

from pypdf import PdfWriter

from carelens.config import Settings
from carelens.openai_client import OpenAIExtractor
from carelens.schemas import CaseNarrative

from conftest import input_document, model_facts


def _pdf_bytes(pages: int = 2) -> bytes:
    writer = PdfWriter()
    for _ in range(pages):
        writer.add_blank_page(width=200, height=200)
    stream = BytesIO()
    writer.write(stream)
    return stream.getvalue()


class FakeResponses:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def parse(self, **kwargs):
        self.calls.append(kwargs)
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


def test_extracts_schema_and_wraps_source_metadata():
    expected = model_facts()
    responses = FakeResponses(
        [SimpleNamespace(output_parsed=None, output_text=expected.model_dump_json())]
    )
    client = SimpleNamespace(responses=responses)
    extractor = OpenAIExtractor(Settings(openai_api_key="test"), client=client)

    document = input_document()
    result = extractor.extract_document(document)

    assert result.source_id == document.source_id
    assert result.facts.patient_id.value == "SYN-2002"
    call = responses.calls[0]
    assert call["model"] == "gpt-5.6-terra"
    assert call["text_format"] is type(expected)
    assert call["instructions"]


def test_synthesis_uses_typed_schema():
    narrative = CaseNarrative(
        headline="Headline",
        summary="Summary",
        attention_summary="Attention",
        uncertainty_summary="Uncertainty",
    )
    responses = FakeResponses([SimpleNamespace(output_parsed=narrative, output_text=None)])
    extractor = OpenAIExtractor(
        Settings(openai_api_key="test"), client=SimpleNamespace(responses=responses)
    )
    assert extractor.synthesize({"priority": "ROUTINE"}) == narrative
    assert responses.calls[0]["text_format"] is CaseNarrative


def test_transient_dns_failure_is_retried(monkeypatch):
    expected = model_facts()
    responses = FakeResponses(
        [
            ConnectionError("getaddrinfo failed"),
            SimpleNamespace(output_parsed=None, output_text=expected.model_dump_json()),
        ]
    )
    monkeypatch.setattr("carelens.openai_client.time.sleep", lambda _: None)
    extractor = OpenAIExtractor(
        Settings(openai_api_key="test"), client=SimpleNamespace(responses=responses)
    )

    result = extractor.extract_document(input_document())

    assert result.facts.patient_name.value == "Jordan Lee"
    assert len(responses.calls) == 2


def test_image_document_defaults_missing_page_to_one():
    expected = model_facts()
    expected.patient_name.page = None
    responses = FakeResponses(
        [SimpleNamespace(output_parsed=None, output_text=expected.model_dump_json())]
    )
    extractor = OpenAIExtractor(
        Settings(openai_api_key="test"), client=SimpleNamespace(responses=responses)
    )
    document = input_document(filename="scan.png")
    document = document.model_copy(update={"mime_type": "image/png", "page_count": 1})

    result = extractor.extract_document(document)

    assert result.facts.patient_name.page == 1


def test_out_of_range_page_is_cleared():
    expected = model_facts()
    expected.patient_name.page = 9
    responses = FakeResponses(
        [SimpleNamespace(output_parsed=None, output_text=expected.model_dump_json())]
    )
    extractor = OpenAIExtractor(
        Settings(openai_api_key="test"), client=SimpleNamespace(responses=responses)
    )
    document = input_document().model_copy(update={"page_count": 2})

    result = extractor.extract_document(document)

    assert result.facts.patient_name.page is None


def test_pdf_pages_are_rasterized_and_labeled_with_page_numbers():
    expected = model_facts()
    responses = FakeResponses(
        [SimpleNamespace(output_parsed=None, output_text=expected.model_dump_json())]
    )
    extractor = OpenAIExtractor(
        Settings(openai_api_key="test"), client=SimpleNamespace(responses=responses)
    )
    document = input_document(filename="doc.pdf").model_copy(
        update={
            "mime_type": "application/pdf",
            "content": _pdf_bytes(pages=2),
            "page_count": 2,
        }
    )

    extractor.extract_document(document)

    sent_input = responses.calls[0]["input"]
    content = sent_input[0]["content"]
    image_parts = [part for part in content if part["type"] == "input_image"]
    label_parts = [part for part in content if part["type"] == "input_text"]
    assert len(image_parts) == 2
    assert all(part["image_url"].startswith("data:image/png;base64,") for part in image_parts)
    assert any("physical page 1 of 2" in part["text"] for part in label_parts)
    assert any("physical page 2 of 2" in part["text"] for part in label_parts)
