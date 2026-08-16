# CareLens Evaluation Report

- Generated (UTC): 2026-08-15T11:27:58.872435+00:00
- Model: `gemini-3.6-flash`
- Grounded narrative synthesis: `disabled`
- Overall: **PASS** (25/25 checks)
- Data: synthetic only

The checks below compare live pipeline outputs with intentionally compact golden expectations. They test routing, key fact recall, conflict rules, and evidence coverage; they are not a clinical validation.

## case_a - PASS

- Checks: 10/10
- Observed priority: `ROUTINE`
- Facts: 17
- Evidence coverage: 100%
- Duration: 79.71s

| Check | Result |
|---|---|
| `priority` | PASS |
| `value:Maya Chen` | PASS |
| `value:SYN-1001` | PASS |
| `value:Azithromycin` | PASS |
| `value:Lisinopril` | PASS |
| `value:2026-08-19` | PASS |
| `forbidden_rule:IDENTITY_MISMATCH` | PASS |
| `forbidden_rule:ALLERGY_RECORD_CONFLICT` | PASS |
| `forbidden_rule:SOURCE_CRITICAL_LAB` | PASS |
| `all_facts_have_evidence` | PASS |

## case_b - PASS

- Checks: 13/13
- Observed priority: `REVIEW NOW`
- Facts: 20
- Evidence coverage: 100%
- Duration: 161.25s

| Check | Result |
|---|---|
| `priority` | PASS |
| `value:Jordan Lee` | PASS |
| `value:SYN-2002` | PASS |
| `value:Penicillin` | PASS |
| `value:Metoprolol` | PASS |
| `value:6.2` | PASS |
| `required_rule:ALLERGY_RECORD_CONFLICT` | PASS |
| `required_rule:MEDICATION_RECONCILIATION` | PASS |
| `required_rule:SOURCE_CRITICAL_LAB` | PASS |
| `required_rule:FOLLOW_UP_INCOMPLETE` | PASS |
| `required_rule:PENDING_ITEM` | PASS |
| `forbidden_rule:IDENTITY_MISMATCH` | PASS |
| `all_facts_have_evidence` | PASS |

Warnings:
- lab_report.pdf: Gemini request failed: Server disconnected without sending a response.

## case_c - PASS

- Checks: 2/2
- Observed priority: `REVIEW SOON`
- Facts: 7
- Evidence coverage: 100%
- Duration: 35.15s

| Check | Result |
|---|---|
| `max_confidence:medium` | PASS |
| `all_facts_have_evidence` | PASS |

## Interpretation

A pass means the POC met its predefined synthetic acceptance checks on this run. It does not establish safety, efficacy, regulatory compliance, or fitness for real patient care.
