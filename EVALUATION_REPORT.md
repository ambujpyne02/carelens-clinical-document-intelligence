# CareLens Evaluation Report

- Generated (UTC): 2026-08-16T07:03:48.441357+00:00
- Model: `gpt-5.6-terra`
- Grounded narrative synthesis: `enabled`
- Overall: **FAIL** (23/25 checks)
- Data: synthetic only

The checks below compare live pipeline outputs with intentionally compact golden expectations. They test routing, key fact recall, conflict rules, and evidence coverage; they are not a clinical validation.

## case_a - FAIL

- Checks: 9/10
- Observed priority: `REVIEW SOON`
- Facts: 21
- Evidence coverage: 100%
- Duration: 20.03s

| Check | Result |
|---|---|
| `priority` | FAIL |
| `value:Maya Chen` | PASS |
| `value:SYN-1001` | PASS |
| `value:Azithromycin` | PASS |
| `value:Lisinopril` | PASS |
| `value:2026-08-19` | PASS |
| `forbidden_rule:IDENTITY_MISMATCH` | PASS |
| `forbidden_rule:ALLERGY_RECORD_CONFLICT` | PASS |
| `forbidden_rule:SOURCE_CRITICAL_LAB` | PASS |
| `all_facts_have_evidence` | PASS |

## case_b - FAIL

- Checks: 12/13
- Observed priority: `REVIEW NOW`
- Facts: 29
- Evidence coverage: 100%
- Duration: 23.76s

| Check | Result |
|---|---|
| `priority` | PASS |
| `value:Jordan Lee` | PASS |
| `value:SYN-2002` | PASS |
| `value:Penicillin` | PASS |
| `value:Metoprolol` | PASS |
| `value:6.2` | PASS |
| `required_rule:ALLERGY_RECORD_CONFLICT` | FAIL |
| `required_rule:MEDICATION_RECONCILIATION` | PASS |
| `required_rule:SOURCE_CRITICAL_LAB` | PASS |
| `required_rule:FOLLOW_UP_INCOMPLETE` | PASS |
| `required_rule:PENDING_ITEM` | PASS |
| `forbidden_rule:IDENTITY_MISMATCH` | PASS |
| `all_facts_have_evidence` | PASS |

## case_c - PASS

- Checks: 2/2
- Observed priority: `REVIEW SOON`
- Facts: 7
- Evidence coverage: 100%
- Duration: 7.40s

| Check | Result |
|---|---|
| `max_confidence:medium` | PASS |
| `all_facts_have_evidence` | PASS |

## Interpretation

A pass means the POC met its predefined synthetic acceptance checks on this run. It does not establish safety, efficacy, regulatory compliance, or fitness for real patient care.
