from __future__ import annotations

import hashlib

import pytest

from carelens.schemas import (
    AllergyFact,
    AlertFact,
    ClinicalFact,
    DocumentFacts,
    DocumentInput,
    EvidenceField,
    FollowUpFact,
    LabFact,
    MedicationFact,
    ModelDocumentFacts,
)


def field(value: str | None, quote: str | None = None) -> EvidenceField:
    return EvidenceField(value=value, page=1 if value else None, quote=quote or value)


def model_facts(
    *,
    patient: str = "Jordan Lee",
    patient_id: str = "SYN-2002",
    dob: str = "1957-11-03",
    medications: list[MedicationFact] | None = None,
    allergies: list[AllergyFact] | None = None,
    labs: list[LabFact] | None = None,
    follow_ups: list[FollowUpFact] | None = None,
    pending_items: list[ClinicalFact] | None = None,
    alerts: list[AlertFact] | None = None,
) -> ModelDocumentFacts:
    return ModelDocumentFacts(
        document_type="physician_note",
        patient_name=field(patient),
        patient_id=field(patient_id),
        date_of_birth=field(dob),
        encounter_date=field("2026-08-14"),
        facility=field("North Valley Medical Center"),
        conditions=[],
        medications=medications or [],
        allergies=allergies or [],
        labs=labs or [],
        follow_ups=follow_ups or [],
        pending_items=pending_items or [],
        explicit_alerts=alerts or [],
        document_summary="Synthetic source summary.",
        limitations=[],
    )


def wrapped(source_id: str, filename: str, facts: ModelDocumentFacts) -> DocumentFacts:
    return DocumentFacts(
        source_id=source_id,
        filename=filename,
        mime_type="text/plain",
        page_count=None,
        facts=facts,
    )


def input_document(filename: str = "note.txt", text: str = "synthetic clinical note") -> DocumentInput:
    content = text.encode("utf-8")
    digest = hashlib.sha256(content).hexdigest()
    return DocumentInput(
        source_id=f"SRC-{digest[:8].upper()}",
        filename=filename,
        mime_type="text/plain",
        size_bytes=len(content),
        sha256=digest,
        content=content,
        page_count=None,
    )


@pytest.fixture
def conflict_documents() -> list[DocumentFacts]:
    discharge = model_facts(
        medications=[
            MedicationFact(
                name="Metoprolol",
                dose="25 mg",
                route="oral",
                frequency="twice daily",
                status="active",
                page=1,
                quote="Metoprolol 25 mg by mouth twice daily - active.",
            )
        ],
        allergies=[
            AllergyFact(
                substance="No known drug allergies",
                reaction=None,
                status="denied",
                scope="general",
                page=1,
                quote="No known drug allergies (NKDA).",
            )
        ],
        labs=[
            LabFact(
                test_name="Potassium",
                value="6.2",
                unit="mmol/L",
                reference_range="3.5-5.1",
                source_flag="critical",
                collected_date="2026-08-14",
                page=1,
                quote="Potassium 6.2 mmol/L - CRITICAL HIGH.",
            )
        ],
        follow_ups=[
            FollowUpFact(
                action="Primary care follow-up",
                provider="Primary care",
                timeframe="within one week",
                status="pending",
                page=1,
                quote="Appointment is not yet scheduled.",
            )
        ],
        pending_items=[
            ClinicalFact(
                value="Repeat potassium test",
                status="current",
                page=1,
                quote="Repeat potassium test is pending.",
            )
        ],
        alerts=[
            AlertFact(
                label="Urgent clinician review required for critical potassium",
                urgency="critical",
                page=1,
                quote="Urgent clinician review is required.",
            )
        ],
    )
    note = model_facts(
        medications=[
            MedicationFact(
                name="Metoprolol",
                dose="50 mg",
                route="oral",
                frequency="twice daily",
                status="changed",
                page=1,
                quote="Metoprolol 50 mg by mouth twice daily - changed dose.",
            )
        ],
        allergies=[
            AllergyFact(
                substance="Penicillin",
                reaction="rash",
                status="confirmed",
                scope="specific",
                page=1,
                quote="Penicillin - rash (confirmed).",
            )
        ],
    )
    return [wrapped("SRC-AAA", "discharge.txt", discharge), wrapped("SRC-BBB", "note.txt", note)]

