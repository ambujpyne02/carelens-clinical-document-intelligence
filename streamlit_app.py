"""CareLens Streamlit application."""

from __future__ import annotations

from html import escape

import streamlit as st

from carelens.config import Settings
from carelens.exports import analysis_to_json, analysis_to_markdown
from carelens.openai_client import ExtractionError
from carelens.ingestion import IngestionError, make_document_input
from carelens.pipeline import AnalysisPipeline
from carelens.samples import load_sample_case, sample_manifest


st.set_page_config(
    page_title="CareLens | Clinical Document Intelligence",
    page_icon="CL",
    layout="wide",
)

st.markdown(
    """
    <style>
    .block-container {max-width: 1180px; padding-top: 1.7rem; padding-bottom: 3rem;}
    .hero {padding: 1.2rem 1.4rem; border-radius: 18px; color: white;
           background: linear-gradient(120deg, #0B5563, #0F766E 58%, #22A699);}
    .hero h1 {margin: 0; font-size: 2.05rem;}
    .hero p {margin: .45rem 0 0; color: #E8FFFA; font-size: 1.02rem;}
    .safety {margin: .8rem 0 1.3rem; padding: .65rem .85rem; border-left: 4px solid #D97706;
             border-radius: 8px; background: #FFF7ED; color: #7C2D12;}
    .priority {display:inline-block; padding:.34rem .68rem; border-radius:999px;
               font-weight:700; letter-spacing:.03em; font-size:.82rem;}
    .review-now {background:#FEE2E2;color:#991B1B}.review-soon {background:#FEF3C7;color:#92400E}
    .routine {background:#DCFCE7;color:#166534}.muted {color:#567085}
    div[data-testid="stMetric"] {background:white; border:1px solid #DCE7EC; padding:.6rem;
                                 border-radius:12px;}
    </style>
    <div class="hero">
      <h1>CareLens</h1>
      <p>Evidence-grounded clinical document intelligence for care-transition review</p>
    </div>
    <div class="safety"><strong>Synthetic demonstration only.</strong> Not for diagnosis, treatment,
    or clinical use. Every output requires qualified human review.</div>
    """,
    unsafe_allow_html=True,
)


def _settings() -> Settings:
    try:
        return Settings.from_env(require_key=True)
    except RuntimeError as exc:
        st.error(str(exc))
        st.stop()


def _render_result(result) -> None:
    css_class = result.priority.lower().replace(" ", "-")
    st.markdown(
        f'<span class="priority {css_class}">{escape(result.priority)}</span>',
        unsafe_allow_html=True,
    )
    st.header(result.narrative.headline)
    st.write(result.narrative.summary)
    st.caption(f"{result.patient_display} | {result.encounter_display}")

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Sources", result.metadata.source_count)
    col2.metric("Evidence-backed facts", len(result.facts))
    col3.metric("Review items", len(result.review_queue))
    col4.metric("Evidence coverage", f"{result.evidence_coverage:.0%}")

    if result.flags:
        st.subheader("Why this needs attention")
        for flag in result.flags:
            with st.container(border=True):
                st.markdown(f"**{flag.priority} - {flag.title}**")
                st.write(flag.rationale)
                for evidence in flag.evidence:
                    location = f" - page {evidence.page}" if evidence.page else ""
                    st.caption(f'{evidence.filename}{location}: "{evidence.quote}"')
    else:
        st.info(
            "No deterministic review rule was triggered. This does not establish "
            "clinical safety; review the sources manually."
        )

    st.subheader("Recommended coordination actions")
    if result.actions:
        for action in result.actions:
            st.markdown(
                f"- **{action.owner.replace('-', ' ').title()} / {action.urgency}:** "
                f"{action.action}"
            )
    else:
        st.write("Continue routine human review of the source documents.")

    tabs = st.tabs(["Structured facts", "Discrepancies", "Source summaries", "Audit details"])
    with tabs[0]:
        categories = sorted({item.category for item in result.facts})
        for category in categories:
            st.markdown(f"#### {category.replace('_', ' ').title()}")
            for fact in [item for item in result.facts if item.category == category]:
                with st.expander(
                    f"{fact.label}: {fact.value} - {fact.confidence.upper()} confidence"
                ):
                    if fact.qualifiers:
                        st.json(fact.qualifiers)
                    for evidence in fact.evidence:
                        location = f"page {evidence.page}" if evidence.page else "location not available"
                        st.markdown(
                            f"**{evidence.filename} - {location}**  \n> {evidence.quote}"
                        )
    with tabs[1]:
        if result.discrepancies:
            for discrepancy in result.discrepancies:
                st.error(discrepancy.title)
                st.write("Compared values: " + " | ".join(discrepancy.values))
        else:
            st.success("No normalized cross-document discrepancies detected.")
    with tabs[2]:
        for filename, summary in result.source_summaries.items():
            st.markdown(f"**{filename}**")
            st.write(summary)
    with tabs[3]:
        st.json(result.metadata.model_dump(mode="json"))
        if result.metadata.warnings:
            for warning in result.metadata.warnings:
                st.warning(warning)

    st.subheader("Download review package")
    left, right = st.columns(2)
    left.download_button(
        "Download structured JSON",
        analysis_to_json(result),
        file_name=f"{result.case_id.lower()}-analysis.json",
        mime="application/json",
        use_container_width=True,
    )
    right.download_button(
        "Download review brief (Markdown)",
        analysis_to_markdown(result),
        file_name=f"{result.case_id.lower()}-review.md",
        mime="text/markdown",
        use_container_width=True,
    )


settings = _settings()
manifest = sample_manifest()
case_options = {
    "Upload my own synthetic documents": "",
    **{
        case["label"]: case_id
        for case_id, case in manifest.get("cases", {}).items()
        if case.get("show_in_app", True)
    },
}

with st.sidebar:
    st.header("Case input")
    selected_label = st.selectbox("Choose a workflow", list(case_options))
    selected_case = case_options[selected_label]
    st.caption("Accepted: PDF, PNG, JPG, JPEG, TXT. Up to 4 files, 10 MB each.")
    if settings.demo_access_code:
        entered_code = st.text_input("Demo access code", type="password")
        access_allowed = entered_code == settings.demo_access_code
    else:
        access_allowed = True
    if st.button("Clear session", use_container_width=True):
        st.session_state.pop("analysis", None)
        st.rerun()

uploaded_files = []
pasted_text = ""
if selected_case:
    case_meta = manifest["cases"][selected_case]
    st.subheader(case_meta["label"])
    st.write(case_meta["description"])
    st.caption("Files: " + ", ".join(case_meta["files"]))
else:
    uploaded_files = st.file_uploader(
        "Upload synthetic clinical documents",
        type=["pdf", "png", "jpg", "jpeg", "txt"],
        accept_multiple_files=True,
        max_upload_size=settings.max_file_mb,
    )
    pasted_text = st.text_area(
        "Or paste synthetic clinical text",
        height=150,
        max_chars=settings.max_text_chars,
    )

if st.button(
    "Analyze case",
    type="primary",
    disabled=not access_allowed,
    use_container_width=True,
):
    try:
        if selected_case:
            documents = load_sample_case(selected_case, settings)
        else:
            documents = [
                make_document_input(file.name, file.getvalue(), settings, file.type)
                for file in uploaded_files
            ]
            if pasted_text.strip():
                documents.append(
                    make_document_input(
                        "pasted_clinical_note.txt",
                        pasted_text.encode("utf-8"),
                        settings,
                        "text/plain",
                    )
                )
        progress_bar = st.progress(0.0, text="Preparing documents")

        def update_progress(current: int, total: int, message: str) -> None:
            progress_bar.progress(min(current / max(total, 1), 1.0), text=message)

        result = AnalysisPipeline(settings).analyze(documents, update_progress)
        progress_bar.empty()
        st.session_state.analysis = result
    except (IngestionError, ExtractionError, KeyError) as exc:
        st.error(str(exc))

if "analysis" in st.session_state:
    st.divider()
    _render_result(st.session_state.analysis)
else:
    st.markdown("### What the prototype demonstrates")
    left, middle, right = st.columns(3)
    left.markdown("**Multimodal extraction**  \nText, PDFs, and document images through OpenAI.")
    middle.markdown("**Auditable reconciliation**  \nEvidence, discrepancies, and derived confidence.")
    right.markdown("**Safe routing**  \nTransparent care-coordination rules, not medical advice.")

