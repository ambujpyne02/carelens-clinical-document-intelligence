# Acceptance Plan

## Product decision

Frame the POC as a **care-transition review accelerator**, not a general medical chatbot. The narrow workflow makes quality visible: assemble a fragmented record, show exactly why an item needs attention, and give a coordinator a bounded next action with source evidence.

## Rubric-to-evidence map

| Evaluation area | Weight | Evidence in this submission |
|---|---:|---|
| AI solution quality | 40% | Native PDF/image ingestion, strict structured output, prompt-injection boundary, deterministic merge/rules, partial-failure fallback, live golden-case evaluation |
| Clinical usefulness | 30% | Evidence quotes and page locations, discrepancy reconciliation, source-labelled critical handling, owner-specific coordination actions, explicit uncertainty and human-review boundary |
| Communication | 15% | Reviewer-first UI, exactly five slides, concise README, five-minute demo path, JSON and Markdown handoff exports |
| Creativity / initiative | 15% | Synthetic mini-benchmark with normal, conflict-heavy, and degraded-image cases; corroboration-based confidence; auditable review queue rather than opaque advice |

## Acceptance gates

1. Offline tests pass with at least 85% package coverage.
2. Live Gemini typed extraction passes using a synthetic text record.
3. Conflict-heavy Case B returns `REVIEW NOW`, recalls the five golden values, fires all five expected rules, and produces 100% evidence coverage.
4. Routine Case A does not produce identity, allergy, or critical-lab false positives.
5. Degraded Case C never promotes an uncorroborated image-only fact above medium confidence.
6. Streamlit starts without an exception and both export formats validate.
7. Every PDF and every slide is rendered and visually inspected.
8. The submission archive contains no credential or virtual environment.


## Likely evaluator questions

**Why use an LLM at all?**  
The hard input problem is multimodal and variable. Gemini performs source-grounded extraction; conventional code owns deterministic reconciliation and routing.

**How do you control hallucination?**  
Strict schemas, evidence quotes, physical page references, prompt-injection instructions, source-stated urgency only, and validated facts as the sole synthesis input. Human review remains required.

**Is the priority clinically validated?**  
No. It is an explainable POC queue derived from synthetic expectations. Production thresholds require prospective evaluation and clinical governance.

**What happens when Gemini fails?**  
One failed document does not discard successful sources. If all extraction fails the case stops clearly; if optional synthesis fails, a deterministic narrative is used.

**What would you build next?**  
FHIR/EHR integration, role-based access, audit logging, approved PHI controls, larger clinician-labeled evaluation sets, calibrated thresholds, monitoring, and a formal escalation workflow.
