"""Transparent care-coordination routing rules over validated facts."""

from __future__ import annotations

import hashlib

from .schemas import ActionItem, Discrepancy, NormalizedFact, ReviewFlag


PRIORITY_RANK = {"ROUTINE": 0, "REVIEW SOON": 1, "REVIEW NOW": 2}


def _stable_id(prefix: str, *parts: str) -> str:
    digest = hashlib.sha1("|".join(parts).encode("utf-8")).hexdigest()[:10]
    return f"{prefix}-{digest.upper()}"


def _flag(
    rule_id: str,
    priority: str,
    title: str,
    rationale: str,
    evidence,
) -> ReviewFlag:
    return ReviewFlag(
        rule_id=rule_id,
        priority=priority,
        title=title,
        rationale=rationale,
        evidence=evidence,
    )


def evaluate_rules(
    facts: list[NormalizedFact], discrepancies: list[Discrepancy]
) -> tuple[str, list[ReviewFlag], list[ActionItem], list[str]]:
    flags: list[ReviewFlag] = []

    for discrepancy in discrepancies:
        if discrepancy.category == "identity":
            flags.append(
                _flag(
                    "IDENTITY_MISMATCH",
                    "REVIEW NOW",
                    "Possible patient identity mismatch",
                    "Identity values differ across the uploaded documents; case merging requires verification.",
                    discrepancy.evidence,
                )
            )
        elif discrepancy.category == "allergy":
            flags.append(
                _flag(
                    "ALLERGY_RECORD_CONFLICT",
                    "REVIEW NOW",
                    "Conflicting allergy documentation",
                    "The sources do not agree on allergy status; a human must reconcile the record.",
                    discrepancy.evidence,
                )
            )
        elif discrepancy.category == "medication":
            flags.append(
                _flag(
                    "MEDICATION_RECONCILIATION",
                    "REVIEW SOON",
                    "Medication details require reconciliation",
                    "Dose, frequency, route, or medication status differs across sources.",
                    discrepancy.evidence,
                )
            )

    for fact in facts:
        if fact.category == "alert" and fact.status in {"critical", "urgent"}:
            flags.append(
                _flag(
                    "SOURCE_EXPLICIT_ALERT",
                    "REVIEW NOW",
                    "Source document contains an explicit urgent alert",
                    "Urgency is copied from the source document and requires clinician review.",
                    fact.evidence,
                )
            )
        elif fact.category == "lab" and fact.status == "critical":
            flags.append(
                _flag(
                    "SOURCE_CRITICAL_LAB",
                    "REVIEW NOW",
                    f"Source-labelled critical result: {fact.label}",
                    "The source explicitly labels this result critical; no independent interpretation was added.",
                    fact.evidence,
                )
            )
        elif fact.category == "lab" and fact.status in {"high", "low", "abnormal"}:
            flags.append(
                _flag(
                    "SOURCE_ABNORMAL_LAB",
                    "REVIEW SOON",
                    f"Source-labelled abnormal result: {fact.label}",
                    "The abnormal label comes directly from the source and should be reviewed in context.",
                    fact.evidence,
                )
            )
        elif fact.category == "follow_up" and (
            fact.status in {"pending", "unknown"}
            or not fact.qualifiers.get("provider")
            or not fact.qualifiers.get("timeframe")
        ):
            flags.append(
                _flag(
                    "FOLLOW_UP_INCOMPLETE",
                    "REVIEW SOON",
                    "Follow-up details are incomplete",
                    "The source does not provide a complete provider and timeframe for follow-up.",
                    fact.evidence,
                )
            )
        elif fact.category == "pending_item" and fact.status not in {
            "negated",
            "resolved",
        }:
            flags.append(
                _flag(
                    "PENDING_ITEM",
                    "REVIEW SOON",
                    "Pending item requires ownership",
                    "The document explicitly identifies an unresolved or pending item.",
                    fact.evidence,
                )
            )

    # Collapse exact repeated rules/evidence while retaining distinct lab titles.
    unique_flags: list[ReviewFlag] = []
    seen: set[tuple[str, str, tuple[str, ...]]] = set()
    for flag in flags:
        key = (
            flag.rule_id,
            flag.title,
            tuple(sorted(item.source_id + ":" + item.quote for item in flag.evidence)),
        )
        if key not in seen:
            seen.add(key)
            unique_flags.append(flag)

    priority = max(
        (flag.priority for flag in unique_flags),
        key=lambda value: PRIORITY_RANK[value],
        default="ROUTINE",
    )

    actions: list[ActionItem] = []
    action_map = {
        "IDENTITY_MISMATCH": (
            "records-team",
            "Verify patient identifiers before combining or acting on these documents.",
        ),
        "ALLERGY_RECORD_CONFLICT": (
            "nurse",
            "Reconcile allergy status against the authoritative patient record.",
        ),
        "MEDICATION_RECONCILIATION": (
            "nurse",
            "Reconcile medication dose, frequency, route, and current status.",
        ),
        "SOURCE_EXPLICIT_ALERT": (
            "clinician",
            "Review the source-labelled urgent alert and document the disposition.",
        ),
        "SOURCE_CRITICAL_LAB": (
            "clinician",
            "Review the source-labelled critical result and document the disposition.",
        ),
        "SOURCE_ABNORMAL_LAB": (
            "clinician",
            "Review the source-labelled abnormal result in the clinical context.",
        ),
        "FOLLOW_UP_INCOMPLETE": (
            "care-coordinator",
            "Confirm the follow-up provider, timeframe, and appointment status.",
        ),
        "PENDING_ITEM": (
            "care-coordinator",
            "Assign an owner and due date for the pending item.",
        ),
    }
    seen_actions: set[str] = set()
    for flag in unique_flags:
        owner, action = action_map[flag.rule_id]
        if action in seen_actions:
            continue
        seen_actions.add(action)
        actions.append(
            ActionItem(
                action_id=_stable_id("ACT", flag.rule_id, action),
                owner=owner,
                urgency=flag.priority,
                action=action,
                rationale=flag.rationale,
                rule_id=flag.rule_id,
            )
        )

    review_queue = [
        item.fact_id for item in facts if item.confidence == "low"
    ] + [item.discrepancy_id for item in discrepancies]
    return priority, unique_flags, actions, review_queue

