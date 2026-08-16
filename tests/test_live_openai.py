from __future__ import annotations

import os

import pytest

from carelens.config import Settings
from carelens.openai_client import OpenAIExtractor
from carelens.ingestion import make_document_input


@pytest.mark.live
@pytest.mark.skipif(
    os.getenv("RUN_LIVE_OPENAI") != "1",
    reason="Set RUN_LIVE_OPENAI=1 to consume live OpenAI quota.",
)
def test_live_structured_extraction():
    settings = Settings.from_env(require_key=True)
    document = make_document_input(
        "live_smoke_note.txt",
        b"SYNTHETIC DEMO. Patient: Test Person. Patient ID: SYN-LIVE-1. No urgent alerts documented.",
        settings,
    )
    result = OpenAIExtractor(settings).extract_document(document)
    assert result.facts.patient_name.value == "Test Person"
    assert result.facts.patient_id.value == "SYN-LIVE-1"
    assert result.facts.explicit_alerts == []
