from carelens.normalize import merge_documents, normalize_text
from carelens.rules import evaluate_rules


def test_normalize_text_is_stable():
    assert normalize_text(" Metoprolol  50-mg ") == "metoprolol 50 mg"


def test_conflicts_generate_expected_review_rules(conflict_documents):
    facts, discrepancies = merge_documents(conflict_documents)
    priority, flags, actions, queue = evaluate_rules(facts, discrepancies)
    rules = {flag.rule_id for flag in flags}

    assert priority == "REVIEW NOW"
    assert "ALLERGY_RECORD_CONFLICT" in rules
    assert "MEDICATION_RECONCILIATION" in rules
    assert "SOURCE_CRITICAL_LAB" in rules
    assert "FOLLOW_UP_INCOMPLETE" in rules
    assert "PENDING_ITEM" in rules
    assert {item.category for item in discrepancies} >= {"medication", "allergy"}
    assert any(item.owner == "clinician" for item in actions)
    assert queue
    assert all(fact.evidence for fact in facts)


def test_corrobated_fact_gets_high_confidence(conflict_documents):
    facts, _ = merge_documents(conflict_documents)
    patient_ids = [item for item in facts if item.label == "patient_id"]
    assert len(patient_ids) == 1
    assert patient_ids[0].confidence == "high"

