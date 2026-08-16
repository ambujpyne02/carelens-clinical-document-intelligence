from __future__ import annotations

from types import SimpleNamespace

from scripts.run_evaluation import evaluate_result


def test_evaluation_checks_priority_values_rules_and_evidence():
    result = SimpleNamespace(
        priority="REVIEW NOW",
        flags=[SimpleNamespace(rule_id="SOURCE_CRITICAL_LAB")],
        facts=[SimpleNamespace(confidence="medium")],
        evidence_coverage=1.0,
        metadata=SimpleNamespace(duration_seconds=1.25, warnings=[]),
        model_dump_json=lambda: '{"patient":"Jordan Lee","value":"6.2"}',
    )
    golden = {
        "priority": "REVIEW NOW",
        "required_values": ["Jordan Lee", "6.2"],
        "required_rules": ["SOURCE_CRITICAL_LAB"],
        "forbidden_rules": ["IDENTITY_MISMATCH"],
        "max_confidence": "medium",
    }

    evaluation = evaluate_result(result, golden)

    assert evaluation["passed"] is True
    assert evaluation["checks_passed"] == evaluation["checks_total"]
