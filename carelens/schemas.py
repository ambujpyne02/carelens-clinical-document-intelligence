"""Typed contracts shared by extraction, validation, rules, UI, and exports."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


DocumentType = Literal[
    "intake_form",
    "discharge_summary",
    "lab_report",
    "physician_note",
    "other",
]
Confidence = Literal["high", "medium", "low", "not_found"]
Priority = Literal["REVIEW NOW", "REVIEW SOON", "ROUTINE"]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class DocumentInput(StrictModel):
    source_id: str
    filename: str
    mime_type: str
    size_bytes: int
    sha256: str
    content: bytes = Field(exclude=True)
    page_count: int | None = None


class EvidenceField(StrictModel):
    value: str | None = Field(description="Exact value stated in the document, or null.")
    page: int | None = Field(description="One-based physical page number, when applicable.")
    quote: str | None = Field(description="Short verbatim supporting quote, or null.")


class ClinicalFact(StrictModel):
    value: str
    status: Literal["current", "historical", "resolved", "negated", "unknown"]
    page: int | None
    quote: str


class MedicationFact(StrictModel):
    name: str
    dose: str | None
    route: str | None
    frequency: str | None
    status: Literal["active", "new", "changed", "stopped", "historical", "unknown"]
    page: int | None
    quote: str


class AllergyFact(StrictModel):
    substance: str
    reaction: str | None
    status: Literal["confirmed", "denied", "historical", "unknown"]
    page: int | None
    quote: str


class LabFact(StrictModel):
    test_name: str
    value: str
    unit: str | None
    reference_range: str | None
    source_flag: Literal["critical", "high", "low", "abnormal", "normal", "not_stated"]
    collected_date: str | None
    page: int | None
    quote: str


class FollowUpFact(StrictModel):
    action: str
    provider: str | None
    timeframe: str | None
    status: Literal["scheduled", "recommended", "pending", "unknown"]
    page: int | None
    quote: str


class AlertFact(StrictModel):
    label: str
    urgency: Literal["critical", "urgent", "other"]
    page: int | None
    quote: str


class ModelDocumentFacts(StrictModel):
    document_type: DocumentType
    patient_name: EvidenceField
    patient_id: EvidenceField
    date_of_birth: EvidenceField
    encounter_date: EvidenceField
    facility: EvidenceField
    conditions: list[ClinicalFact]
    medications: list[MedicationFact]
    allergies: list[AllergyFact]
    labs: list[LabFact]
    follow_ups: list[FollowUpFact]
    pending_items: list[ClinicalFact]
    explicit_alerts: list[AlertFact]
    document_summary: str
    limitations: list[str]


class DocumentFacts(StrictModel):
    source_id: str
    filename: str
    mime_type: str
    page_count: int | None = None
    facts: ModelDocumentFacts


class Provenance(StrictModel):
    source_id: str
    filename: str
    page: int | None
    quote: str


class NormalizedFact(StrictModel):
    fact_id: str
    category: Literal[
        "identity",
        "encounter",
        "condition",
        "medication",
        "allergy",
        "lab",
        "follow_up",
        "pending_item",
        "alert",
    ]
    label: str
    value: str
    qualifiers: dict[str, str | None] = Field(default_factory=dict)
    status: str
    confidence: Confidence
    evidence: list[Provenance]


class Discrepancy(StrictModel):
    discrepancy_id: str
    category: Literal["identity", "medication", "allergy", "other"]
    title: str
    values: list[str]
    severity: Literal["high", "medium", "low"]
    evidence: list[Provenance]


class ReviewFlag(StrictModel):
    rule_id: str
    priority: Priority
    title: str
    rationale: str
    evidence: list[Provenance]


class ActionItem(StrictModel):
    action_id: str
    owner: Literal["clinician", "nurse", "care-coordinator", "records-team"]
    urgency: Priority
    action: str
    rationale: str
    rule_id: str


class CaseNarrative(StrictModel):
    headline: str
    summary: str
    attention_summary: str
    uncertainty_summary: str


class ProcessingMetadata(StrictModel):
    model_id: str
    prompt_version: str
    pipeline_version: str
    duration_seconds: float
    source_count: int
    generated_at_utc: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    warnings: list[str] = Field(default_factory=list)


class AnalysisResult(StrictModel):
    case_id: str
    priority: Priority
    patient_display: str
    encounter_display: str
    narrative: CaseNarrative
    facts: list[NormalizedFact]
    discrepancies: list[Discrepancy]
    flags: list[ReviewFlag]
    actions: list[ActionItem]
    review_queue: list[str]
    source_summaries: dict[str, str]
    evidence_coverage: float
    metadata: ProcessingMetadata
