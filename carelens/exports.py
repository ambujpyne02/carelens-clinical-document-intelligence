"""Human-readable and machine-readable output serialization."""

from __future__ import annotations

import json

from .schemas import AnalysisResult


def analysis_to_json(result: AnalysisResult) -> str:
    return json.dumps(result.model_dump(mode="json"), indent=2, ensure_ascii=False)


def analysis_to_markdown(result: AnalysisResult) -> str:
    lines = [
        "# CareLens Patient Review Brief",
        "",
        "> Synthetic demonstration only - not for clinical use.",
        "",
        f"**Case:** {result.case_id}",
        f"**Priority:** {result.priority}",
        f"**Patient:** {result.patient_display}",
        f"**Encounter:** {result.encounter_display}",
        "",
        "## Summary",
        "",
        result.narrative.headline,
        "",
        result.narrative.summary,
        "",
        f"**Attention:** {result.narrative.attention_summary}",
        "",
        f"**Uncertainty:** {result.narrative.uncertainty_summary}",
        "",
        "## Review flags",
        "",
    ]
    if result.flags:
        for flag in result.flags:
            lines.append(f"- **{flag.priority} - {flag.title}:** {flag.rationale}")
    else:
        lines.append("- No deterministic review rule was triggered.")
    lines.extend(["", "## Recommended coordination actions", ""])
    if result.actions:
        for action in result.actions:
            lines.append(
                f"- **{action.owner} / {action.urgency}:** {action.action}"
            )
    else:
        lines.append("- Continue routine human review of the source documents.")
    lines.extend(["", "## Evidence-backed facts", ""])
    for fact in result.facts:
        lines.append(
            f"- **{fact.category.title()} - {fact.label}:** {fact.value} "
            f"({fact.confidence} confidence)"
        )
        for evidence in fact.evidence:
            location = f", page {evidence.page}" if evidence.page else ""
            lines.append(
                f"  - `{evidence.filename}{location}`: \"{evidence.quote}\""
            )
    lines.extend(
        [
            "",
            "## Processing metadata",
            "",
            f"- Model: `{result.metadata.model_id}`",
            f"- Pipeline: `{result.metadata.pipeline_version}`",
            f"- Evidence coverage: {result.evidence_coverage:.0%}",
            f"- Duration: {result.metadata.duration_seconds:.2f} seconds",
        ]
    )
    return "\n".join(lines) + "\n"

