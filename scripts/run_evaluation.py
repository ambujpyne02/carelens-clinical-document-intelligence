"""Run reproducible golden-case acceptance checks against the live pipeline."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from carelens.config import Settings  # noqa: E402
from carelens.exports import analysis_to_json, analysis_to_markdown  # noqa: E402
from carelens.pipeline import AnalysisPipeline  # noqa: E402
from carelens.samples import load_sample_case, sample_manifest  # noqa: E402


CONFIDENCE_RANK = {"not_found": 0, "low": 1, "medium": 2, "high": 3}


def evaluate_result(result: Any, golden: dict[str, Any]) -> dict[str, Any]:
    """Compare a validated AnalysisResult with a compact golden expectation."""

    serialized = result.model_dump_json().casefold()
    rule_ids = {flag.rule_id for flag in result.flags}
    checks: dict[str, bool] = {}

    if "priority" in golden:
        checks["priority"] = result.priority == golden["priority"]
    for value in golden.get("required_values", []):
        checks[f"value:{value}"] = value.casefold() in serialized
    for rule_id in golden.get("required_rules", []):
        checks[f"required_rule:{rule_id}"] = rule_id in rule_ids
    for rule_id in golden.get("forbidden_rules", []):
        checks[f"forbidden_rule:{rule_id}"] = rule_id not in rule_ids

    if "max_confidence" in golden:
        maximum = max(
            (CONFIDENCE_RANK[fact.confidence] for fact in result.facts),
            default=0,
        )
        checks[f"max_confidence:{golden['max_confidence']}"] = (
            maximum <= CONFIDENCE_RANK[golden["max_confidence"]]
        )

    checks["all_facts_have_evidence"] = result.evidence_coverage == 1.0
    passed = sum(checks.values())
    return {
        "passed": passed == len(checks),
        "checks_passed": passed,
        "checks_total": len(checks),
        "checks": checks,
        "observed_priority": result.priority,
        "observed_rule_ids": sorted(rule_ids),
        "fact_count": len(result.facts),
        "evidence_coverage": result.evidence_coverage,
        "duration_seconds": result.metadata.duration_seconds,
        "warnings": result.metadata.warnings,
    }


def render_report(
    records: list[dict[str, Any]], *, model: str, synthesis_enabled: bool
) -> str:
    total_passed = sum(record["evaluation"]["checks_passed"] for record in records)
    total_checks = sum(record["evaluation"]["checks_total"] for record in records)
    all_passed = all(record["evaluation"]["passed"] for record in records)
    lines = [
        "# CareLens Evaluation Report",
        "",
        f"- Generated (UTC): {datetime.now(timezone.utc).isoformat()}",
        f"- Model: `{model}`",
        f"- Grounded narrative synthesis: `{'enabled' if synthesis_enabled else 'disabled'}`",
        f"- Overall: **{'PASS' if all_passed else 'FAIL'}** ({total_passed}/{total_checks} checks)",
        "- Data: synthetic only",
        "",
        "The checks below compare live pipeline outputs with intentionally compact golden expectations. "
        "They test routing, key fact recall, conflict rules, and evidence coverage; they are not a clinical validation.",
        "",
    ]
    for record in records:
        evaluation = record["evaluation"]
        lines.extend(
            [
                f"## {record['case_id']} - {'PASS' if evaluation['passed'] else 'FAIL'}",
                "",
                f"- Checks: {evaluation['checks_passed']}/{evaluation['checks_total']}",
                f"- Observed priority: `{evaluation['observed_priority']}`",
                f"- Facts: {evaluation['fact_count']}",
                f"- Evidence coverage: {evaluation['evidence_coverage']:.0%}",
                f"- Duration: {evaluation['duration_seconds']:.2f}s",
                "",
                "| Check | Result |",
                "|---|---|",
            ]
        )
        for name, passed in evaluation["checks"].items():
            lines.append(f"| `{name}` | {'PASS' if passed else 'FAIL'} |")
        if evaluation["warnings"]:
            lines.extend(["", "Warnings:"])
            lines.extend(f"- {warning}" for warning in evaluation["warnings"])
        lines.append("")
    lines.extend(
        [
            "## Interpretation",
            "",
            "A pass means the POC met its predefined synthetic acceptance checks on this run. "
            "It does not establish safety, efficacy, regulatory compliance, or fitness for real patient care.",
            "",
        ]
    )
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--cases",
        nargs="+",
        default=["case_a", "case_b", "case_c"],
        help="Manifest case IDs to evaluate.",
    )
    parser.add_argument(
        "--no-synthesis",
        action="store_true",
        help="Skip the optional second OpenAI call that rewrites the deterministic narrative.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=PROJECT_ROOT / "output" / "evaluation",
    )
    parser.add_argument(
        "--append",
        action="store_true",
        help="Merge these case results into an existing evaluation summary.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    settings = Settings.from_env(require_key=True)
    if args.no_synthesis:
        settings = replace(settings, enable_synthesis=False)
    manifest = sample_manifest()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    records: list[dict[str, Any]] = []
    summary_path = args.output_dir / "evaluation_summary.json"
    if args.append and summary_path.exists():
        previous = json.loads(summary_path.read_text(encoding="utf-8"))
        records = list(previous.get("cases", []))

    for case_id in args.cases:
        if case_id not in manifest.get("cases", {}):
            raise SystemExit(f"Unknown case ID: {case_id}")
        case = manifest["cases"][case_id]
        golden_path = PROJECT_ROOT / case["golden"]
        golden = json.loads(golden_path.read_text(encoding="utf-8"))
        print(f"[{case_id}] loading {len(case['files'])} synthetic source(s)", flush=True)
        documents = load_sample_case(case_id, settings)

        def progress(current: int, total: int, message: str) -> None:
            print(f"[{case_id}] {current}/{total} {message}", flush=True)

        result = AnalysisPipeline(settings).analyze(documents, progress)
        evaluation = evaluate_result(result, golden)
        (args.output_dir / f"{case_id}_analysis.json").write_text(
            analysis_to_json(result), encoding="utf-8"
        )
        (args.output_dir / f"{case_id}_review.md").write_text(
            analysis_to_markdown(result), encoding="utf-8"
        )
        record = {"case_id": case_id, "evaluation": evaluation}
        records = [item for item in records if item.get("case_id") != case_id]
        records.append(record)
        print(
            f"[{case_id}] {'PASS' if evaluation['passed'] else 'FAIL'} "
            f"({evaluation['checks_passed']}/{evaluation['checks_total']})",
            flush=True,
        )

    summary = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "model": settings.openai_model,
        "synthesis_enabled": settings.enable_synthesis,
        "all_passed": all(item["evaluation"]["passed"] for item in records),
        "cases": records,
    }
    records.sort(key=lambda item: item["case_id"])
    summary_path.write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )
    report = render_report(
        records,
        model=settings.openai_model,
        synthesis_enabled=settings.enable_synthesis,
    )
    (PROJECT_ROOT / "EVALUATION_REPORT.md").write_text(report, encoding="utf-8")
    print(f"Report: {PROJECT_ROOT / 'EVALUATION_REPORT.md'}", flush=True)
    return 0 if summary["all_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
