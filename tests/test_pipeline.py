from __future__ import annotations

from carelens.config import Settings
from carelens.exports import analysis_to_json, analysis_to_markdown
from carelens.pipeline import AnalysisPipeline
from carelens.schemas import CaseNarrative

from conftest import input_document, model_facts, wrapped


class FakeExtractor:
    def extract_document(self, document):
        return wrapped(document.source_id, document.filename, model_facts())

    def synthesize(self, payload):
        return CaseNarrative(
            headline="Grounded synthetic headline",
            summary="Validated synthetic summary.",
            attention_summary="No source-supported alert.",
            uncertainty_summary="No discrepancy detected.",
        )


def test_pipeline_builds_exportable_result():
    settings = Settings(openai_api_key="test", enable_synthesis=True)
    result = AnalysisPipeline(settings, extractor=FakeExtractor()).analyze(
        [input_document()]
    )

    assert result.priority == "ROUTINE"
    assert result.narrative.headline == "Grounded synthetic headline"
    assert result.evidence_coverage == 1.0
    assert "OPENAI_API_KEY" not in analysis_to_json(result)
    markdown = analysis_to_markdown(result)
    assert "Synthetic demonstration only" in markdown
    assert result.case_id in markdown

