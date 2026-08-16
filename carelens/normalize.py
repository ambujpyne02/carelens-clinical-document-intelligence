"""Deterministic normalization, evidence aggregation, and discrepancy detection."""

from __future__ import annotations

import hashlib
import re
from collections import defaultdict
from typing import Any, Iterable

from .schemas import (
    Discrepancy,
    DocumentFacts,
    NormalizedFact,
    Provenance,
)


def normalize_text(value: str | None) -> str:
    if not value:
        return ""
    return re.sub(r"[^a-z0-9]+", " ", value.casefold()).strip()


def _stable_id(prefix: str, *parts: str) -> str:
    digest = hashlib.sha1("|".join(parts).encode("utf-8")).hexdigest()[:10]
    return f"{prefix}-{digest.upper()}"


def _provenance(document: DocumentFacts, page: int | None, quote: str) -> Provenance:
    return Provenance(
        source_id=document.source_id,
        filename=document.filename,
        page=page,
        quote=quote,
    )


def _dedupe_evidence(evidence: Iterable[Provenance]) -> list[Provenance]:
    seen: set[tuple[str, int | None, str]] = set()
    unique: list[Provenance] = []
    for item in evidence:
        key = (item.source_id, item.page, item.quote)
        if key not in seen:
            seen.add(key)
            unique.append(item)
    return unique


def _confidence(evidence: list[Provenance], *, conflicted: bool = False) -> str:
    if not evidence:
        return "not_found"
    if conflicted:
        return "low"
    if len({item.source_id for item in evidence}) >= 2:
        return "high"
    return "medium"


def _make_fact(
    category: str,
    label: str,
    value: str,
    status: str,
    qualifiers: dict[str, str | None],
    evidence: list[Provenance],
    *,
    conflicted: bool = False,
) -> NormalizedFact:
    evidence = _dedupe_evidence(evidence)
    key = normalize_text(value) + "|" + "|".join(
        f"{name}:{normalize_text(val)}" for name, val in sorted(qualifiers.items())
    )
    return NormalizedFact(
        fact_id=_stable_id("FACT", category, label, key),
        category=category,
        label=label,
        value=value,
        qualifiers=qualifiers,
        status=status,
        confidence=_confidence(evidence, conflicted=conflicted),
        evidence=evidence,
    )


def _discrepancy(
    category: str,
    title: str,
    values: list[str],
    severity: str,
    evidence: list[Provenance],
) -> Discrepancy:
    return Discrepancy(
        discrepancy_id=_stable_id("DISC", category, title, *sorted(values)),
        category=category,
        title=title,
        values=sorted(set(values)),
        severity=severity,
        evidence=_dedupe_evidence(evidence),
    )


def merge_documents(
    documents: list[DocumentFacts],
) -> tuple[list[NormalizedFact], list[Discrepancy]]:
    facts: list[NormalizedFact] = []
    discrepancies: list[Discrepancy] = []

    # Identity and encounter fields.
    field_specs = [
        ("patient_name", "identity", "Patient name", "medium"),
        ("patient_id", "identity", "Patient ID", "high"),
        ("date_of_birth", "identity", "Date of birth", "high"),
        ("encounter_date", "encounter", "Encounter date", "medium"),
        ("facility", "encounter", "Facility", "low"),
    ]
    for attribute, category, label, severity in field_specs:
        groups: dict[str, dict[str, Any]] = {}
        for document in documents:
            field = getattr(document.facts, attribute)
            if not field.value:
                continue
            key = normalize_text(field.value)
            record = groups.setdefault(
                key, {"value": field.value, "evidence": []}
            )
            record["evidence"].append(
                _provenance(document, field.page, field.quote or field.value)
            )
        conflicted = len(groups) > 1
        for record in groups.values():
            facts.append(
                _make_fact(
                    category,
                    attribute,
                    record["value"],
                    "stated",
                    {},
                    record["evidence"],
                    conflicted=conflicted,
                )
            )
        if conflicted:
            discrepancies.append(
                _discrepancy(
                    "identity" if category == "identity" else "other",
                    f"Conflicting {label.lower()}",
                    [record["value"] for record in groups.values()],
                    severity,
                    [item for record in groups.values() for item in record["evidence"]],
                )
            )

    # Simple repeated facts: conditions and pending items.
    for attribute, category, label in [
        ("conditions", "condition", "Condition"),
        ("pending_items", "pending_item", "Pending item"),
    ]:
        groups: dict[tuple[str, str], dict[str, Any]] = {}
        for document in documents:
            for item in getattr(document.facts, attribute):
                key = (normalize_text(item.value), item.status)
                record = groups.setdefault(
                    key,
                    {
                        "value": item.value,
                        "status": item.status,
                        "evidence": [],
                    },
                )
                record["evidence"].append(
                    _provenance(document, item.page, item.quote)
                )
        for record in groups.values():
            facts.append(
                _make_fact(
                    category,
                    label,
                    record["value"],
                    record["status"],
                    {},
                    record["evidence"],
                )
            )

    # Medications, with reconciliation across sources.
    medication_groups: dict[str, dict[tuple[str, str, str, str], dict[str, Any]]] = defaultdict(dict)
    for document in documents:
        for item in document.facts.medications:
            name_key = normalize_text(item.name)
            variant_key = (
                normalize_text(item.dose),
                normalize_text(item.route),
                normalize_text(item.frequency),
                item.status,
            )
            record = medication_groups[name_key].setdefault(
                variant_key,
                {
                    "name": item.name,
                    "dose": item.dose,
                    "route": item.route,
                    "frequency": item.frequency,
                    "status": item.status,
                    "evidence": [],
                },
            )
            record["evidence"].append(_provenance(document, item.page, item.quote))

    for variants in medication_groups.values():
        conflicted = len(variants) > 1
        for record in variants.values():
            pieces = [record["name"]]
            pieces.extend(
                value
                for value in (record["dose"], record["route"], record["frequency"])
                if value
            )
            facts.append(
                _make_fact(
                    "medication",
                    record["name"],
                    " - ".join(pieces),
                    record["status"],
                    {
                        "dose": record["dose"],
                        "route": record["route"],
                        "frequency": record["frequency"],
                    },
                    record["evidence"],
                    conflicted=conflicted,
                )
            )
        if conflicted:
            values = [
                " / ".join(
                    value
                    for value in (
                        record["name"],
                        record["dose"],
                        record["route"],
                        record["frequency"],
                        record["status"],
                    )
                    if value
                )
                for record in variants.values()
            ]
            discrepancies.append(
                _discrepancy(
                    "medication",
                    f"Medication details differ for {next(iter(variants.values()))['name']}",
                    values,
                    "medium",
                    [item for record in variants.values() for item in record["evidence"]],
                )
            )

    # Allergies, including NKDA versus a stated allergy.
    allergy_groups: dict[str, dict[tuple[str, str], dict[str, Any]]] = defaultdict(dict)
    all_allergy_records: list[dict[str, Any]] = []
    for document in documents:
        for item in document.facts.allergies:
            substance_key = normalize_text(item.substance)
            variant_key = (normalize_text(item.reaction), item.status)
            record = allergy_groups[substance_key].setdefault(
                variant_key,
                {
                    "substance": item.substance,
                    "reaction": item.reaction,
                    "status": item.status,
                    "evidence": [],
                },
            )
            record["evidence"].append(_provenance(document, item.page, item.quote))
            all_allergy_records.append(record)

    nkda_keys = {"nkda", "no known drug allergies", "no known allergies"}
    has_nkda = any(key in nkda_keys for key in allergy_groups)
    has_confirmed = any(
        key not in nkda_keys
        and any(record["status"] == "confirmed" for record in variants.values())
        for key, variants in allergy_groups.items()
    )
    global_allergy_conflict = has_nkda and has_confirmed
    for variants in allergy_groups.values():
        local_conflict = len({record["status"] for record in variants.values()}) > 1
        for record in variants.values():
            value = record["substance"]
            if record["reaction"]:
                value += f" ({record['reaction']})"
            facts.append(
                _make_fact(
                    "allergy",
                    record["substance"],
                    value,
                    record["status"],
                    {"reaction": record["reaction"]},
                    record["evidence"],
                    conflicted=local_conflict or global_allergy_conflict,
                )
            )
        if local_conflict:
            discrepancies.append(
                _discrepancy(
                    "allergy",
                    f"Allergy status differs for {next(iter(variants.values()))['substance']}",
                    [record["status"] for record in variants.values()],
                    "high",
                    [item for record in variants.values() for item in record["evidence"]],
                )
            )
    if global_allergy_conflict:
        discrepancies.append(
            _discrepancy(
                "allergy",
                "NKDA conflicts with a documented drug allergy",
                [record["substance"] for record in all_allergy_records],
                "high",
                [item for record in all_allergy_records for item in record["evidence"]],
            )
        )

    # Labs, follow-ups, and explicit source alerts.
    lab_groups: dict[tuple[str, str, str, str], dict[str, Any]] = {}
    for document in documents:
        for item in document.facts.labs:
            key = (
                normalize_text(item.test_name),
                normalize_text(item.collected_date),
                normalize_text(item.value),
                normalize_text(item.unit),
            )
            record = lab_groups.setdefault(
                key,
                {
                    "item": item,
                    "evidence": [],
                },
            )
            record["evidence"].append(_provenance(document, item.page, item.quote))
    for record in lab_groups.values():
        item = record["item"]
        value = f"{item.test_name}: {item.value}{(' ' + item.unit) if item.unit else ''}"
        facts.append(
            _make_fact(
                "lab",
                item.test_name,
                value,
                item.source_flag,
                {
                    "unit": item.unit,
                    "reference_range": item.reference_range,
                    "collected_date": item.collected_date,
                    "source_flag": item.source_flag,
                },
                record["evidence"],
            )
        )

    follow_groups: dict[tuple[str, str, str, str], dict[str, Any]] = {}
    for document in documents:
        for item in document.facts.follow_ups:
            key = (
                normalize_text(item.action),
                normalize_text(item.provider),
                normalize_text(item.timeframe),
                item.status,
            )
            record = follow_groups.setdefault(key, {"item": item, "evidence": []})
            record["evidence"].append(_provenance(document, item.page, item.quote))
    for record in follow_groups.values():
        item = record["item"]
        facts.append(
            _make_fact(
                "follow_up",
                "Follow-up",
                item.action,
                item.status,
                {"provider": item.provider, "timeframe": item.timeframe},
                record["evidence"],
            )
        )

    alert_groups: dict[tuple[str, str], dict[str, Any]] = {}
    for document in documents:
        for item in document.facts.explicit_alerts:
            key = (normalize_text(item.label), item.urgency)
            record = alert_groups.setdefault(key, {"item": item, "evidence": []})
            record["evidence"].append(_provenance(document, item.page, item.quote))
    for record in alert_groups.values():
        item = record["item"]
        facts.append(
            _make_fact(
                "alert",
                "Source alert",
                item.label,
                item.urgency,
                {},
                record["evidence"],
            )
        )

    facts.sort(key=lambda item: (item.category, item.label.casefold(), item.value.casefold()))
    discrepancies.sort(key=lambda item: (item.severity, item.category, item.title))
    return facts, discrepancies

