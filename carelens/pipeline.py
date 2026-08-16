"""End-to-end orchestration from validated documents to review-ready output."""

from __future__ import annotations

import hashlib
import time
from collections.abc import Callable
from typing import Any

from .config import Settings
from .openai_client import ExtractionError, OpenAIExtractor, PROMPT_VERSION
from .ingestion import validate_batch
from .normalize import merge_documents
from .rules import PRIORITY_RANK, evaluate_rules
from .schemas import (
    AnalysisResult,
    CaseNarrative,
    DocumentInput,
    NormalizedFact,
    ProcessingMetadata,
)


ProgressCallback = Callable[[int, int, str], None]


def _best_fact(facts: list[NormalizedFact], label: str) -> NormalizedFact | None:
    candidates = [item for item in facts if item.label == label]
    rank = {"high": 3, "medium": 2, "low": 1, "not_found": 0}
    return max(
        candidates,
        key=lambda item: (rank[item.confidence], len(item.evidence)),
        default=None,
    )


def _fallback_narrative(
    patient_display: str,
    source_count: int,
    fact_count: int,
    priority: str,
    flags,
    discrepancies,
) -> CaseNarrative:
    if priority == "ROUTINE":
        headline = "No source-supported coordination alerts detected"
        attention = (
            "No deterministic review rule was triggered. This does not establish "
            "clinical safety; the source documents still require human review."
        )
    else:
        headline = f"{priority.title()}: {len(flags)} evidence-supported review item(s)"
        attention = "; ".join(flag.title for flag in flags[:3])
    uncertainty = (
        f"{len(discrepancies)} cross-document discrepancy(ies) require verification."
        if discrepancies
        else "No cross-document contradictions were detected in the supplied sources."
    )
    return CaseNarrative(
        headline=headline,
        summary=(
            f"{patient_display} has {fact_count} evidence-backed facts extracted "
            f"from {source_count} synthetic source document(s)."
        ),
        attention_summary=attention,
        uncertainty_summary=uncertainty,
    )


class AnalysisPipeline:
    def __init__(
        self,
        settings: Settings,
        extractor: OpenAIExtractor | Any | None = None,
    ) -> None:
        self.settings = settings
        self.extractor = extractor or OpenAIExtractor(settings)

    def analyze(
        self,
        documents: list[DocumentInput],
        progress: ProgressCallback | None = None,
    ) -> AnalysisResult:
        started = time.perf_counter()
        documents, warnings = validate_batch(documents, self.settings)
        total_steps = len(documents) + 2
        extracted = []

        for index, document in enumerate(documents, start=1):
            if progress:
                progress(index - 1, total_steps, f"Extracting {document.filename}")
            try:
                extracted.append(self.extractor.extract_document(document))
            except ExtractionError as exc:
                warnings.append(f"{document.filename}: {exc}")

        if not extracted:
            raise ExtractionError("No document could be extracted successfully.")

        if progress:
            progress(len(documents), total_steps, "Reconciling facts and applying review rules")
        facts, discrepancies = merge_documents(extracted)
        priority, flags, actions, review_queue = evaluate_rules(facts, discrepancies)

        patient_name = _best_fact(facts, "patient_name")
        patient_id = _best_fact(facts, "patient_id")
        encounter_date = _best_fact(facts, "encounter_date")
        facility = _best_fact(facts, "facility")
        patient_display = patient_name.value if patient_name else "Patient identity not found"
        if patient_id:
            patient_display += f" ({patient_id.value})"
        if any(item.category == "identity" for item in discrepancies):
            patient_display += " - verify identity"
        encounter_parts = [
            item.value for item in (encounter_date, facility) if item is not None
        ]
        encounter_display = " | ".join(encounter_parts) or "Encounter details not found"

        narrative = _fallback_narrative(
            patient_display,
            len(extracted),
            len(facts),
            priority,
            flags,
            discrepancies,
        )
        if self.settings.enable_synthesis:
            if progress:
                progress(total_steps - 1, total_steps, "Generating grounded case narrative")
            synthesis_payload = {
                "patient": patient_display,
                "encounter": encounter_display,
                "priority": priority,
                "facts": [
                    {
                        "fact_id": item.fact_id,
                        "category": item.category,
                        "value": item.value,
                        "status": item.status,
                        "confidence": item.confidence,
                    }
                    for item in facts
                ],
                "discrepancies": [
                    {
                        "id": item.discrepancy_id,
                        "title": item.title,
                        "values": item.values,
                    }
                    for item in discrepancies
                ],
                "flags": [
                    {
                        "rule_id": item.rule_id,
                        "title": item.title,
                        "rationale": item.rationale,
                    }
                    for item in flags
                ],
                "actions": [
                    {
                        "owner": item.owner,
                        "action": item.action,
                        "rationale": item.rationale,
                    }
                    for item in actions
                ],
            }
            try:
                narrative = self.extractor.synthesize(synthesis_payload)
            except ExtractionError as exc:
                warnings.append(f"Grounded synthesis fallback used: {exc}")

        evidence_coverage = (
            sum(bool(item.evidence) for item in facts) / len(facts) if facts else 0.0
        )
        digest = hashlib.sha256(
            "|".join(sorted(document.sha256 for document in documents)).encode("utf-8")
        ).hexdigest()[:10]
        if progress:
            progress(total_steps, total_steps, "Complete")
        return AnalysisResult(
            case_id=f"CASE-{digest.upper()}",
            priority=priority,
            patient_display=patient_display,
            encounter_display=encounter_display,
            narrative=narrative,
            facts=facts,
            discrepancies=discrepancies,
            flags=sorted(
                flags,
                key=lambda item: (-PRIORITY_RANK[item.priority], item.title),
            ),
            actions=sorted(
                actions,
                key=lambda item: (-PRIORITY_RANK[item.urgency], item.owner),
            ),
            review_queue=review_queue,
            source_summaries={
                item.filename: item.facts.document_summary for item in extracted
            },
            evidence_coverage=round(evidence_coverage, 3),
            metadata=ProcessingMetadata(
                model_id=self.settings.openai_model,
                prompt_version=PROMPT_VERSION,
                pipeline_version="1.0.0",
                duration_seconds=round(time.perf_counter() - started, 2),
                source_count=len(extracted),
                warnings=warnings,
            ),
        )

