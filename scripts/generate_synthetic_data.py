"""Generate clearly labelled, fictional clinical documents for the demo."""

from __future__ import annotations

import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


ROOT = Path(__file__).resolve().parent.parent
DATA_ROOT = ROOT / "sample_data"


def _font(size: int, *, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    names = ["arialbd.ttf" if bold else "arial.ttf", "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"]
    for name in names:
        try:
            return ImageFont.truetype(name, size=size)
        except OSError:
            continue
    return ImageFont.load_default()


def _page(canvas, doc) -> None:
    width, height = LETTER
    canvas.saveState()
    canvas.setFillColor(colors.HexColor("#B91C1C"))
    canvas.setFont("Helvetica-Bold", 9)
    canvas.drawCentredString(width / 2, height - 24, "SYNTHETIC DEMO - NOT A REAL PATIENT")
    canvas.setStrokeColor(colors.HexColor("#D6E4E8"))
    canvas.line(54, 36, width - 54, 36)
    canvas.setFillColor(colors.HexColor("#60758A"))
    canvas.setFont("Helvetica", 8)
    canvas.drawString(54, 24, "CareLens evaluation dataset")
    canvas.drawRightString(width - 54, 24, f"Page {doc.page}")
    canvas.restoreState()


def create_clinical_pdf(path: Path, title: str, metadata: list[tuple[str, str]], sections: list[tuple[str, list[str]]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    styles = getSampleStyleSheet()
    styles.add(
        ParagraphStyle(
            name="DocTitle",
            parent=styles["Title"],
            fontName="Helvetica-Bold",
            fontSize=20,
            leading=24,
            textColor=colors.HexColor("#17324D"),
            spaceAfter=14,
        )
    )
    styles.add(
        ParagraphStyle(
            name="Section",
            parent=styles["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=11,
            leading=14,
            textColor=colors.HexColor("#0F766E"),
            spaceBefore=10,
            spaceAfter=5,
        )
    )
    styles.add(
        ParagraphStyle(
            name="BodyClinical",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=9.5,
            leading=13,
            textColor=colors.HexColor("#1F3447"),
            spaceAfter=5,
        )
    )
    styles.add(
        ParagraphStyle(
            name="SyntheticBanner",
            parent=styles["BodyText"],
            fontName="Helvetica-Bold",
            fontSize=9,
            leading=12,
            alignment=TA_CENTER,
            textColor=colors.HexColor("#991B1B"),
            backColor=colors.HexColor("#FEE2E2"),
            borderPadding=6,
            spaceAfter=14,
        )
    )

    doc = SimpleDocTemplate(
        str(path),
        pagesize=LETTER,
        rightMargin=0.7 * inch,
        leftMargin=0.7 * inch,
        topMargin=0.65 * inch,
        bottomMargin=0.6 * inch,
        title=title,
        author="CareLens Synthetic Dataset",
    )
    story = [
        Paragraph(title, styles["DocTitle"]),
        Paragraph("SYNTHETIC DEMO - NOT A REAL PATIENT", styles["SyntheticBanner"]),
    ]
    meta_table = Table(
        [[Paragraph(f"<b>{key}</b>", styles["BodyClinical"]), Paragraph(value, styles["BodyClinical"])] for key, value in metadata],
        colWidths=[1.45 * inch, 5.25 * inch],
        hAlign="LEFT",
    )
    meta_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#E8F3F1")),
                ("GRID", (0, 0), (-1, -1), 0.45, colors.HexColor("#C7DADF")),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    story.extend([meta_table, Spacer(1, 9)])
    for heading, paragraphs in sections:
        story.append(Paragraph(heading, styles["Section"]))
        for paragraph in paragraphs:
            story.append(Paragraph(paragraph, styles["BodyClinical"]))
    doc.build(story, onFirstPage=_page, onLaterPages=_page)


def create_intake_image(path: Path, *, degraded: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    image = Image.new("RGB", (1500, 1900), "white")
    draw = ImageDraw.Draw(image)
    navy = "#17324D"
    teal = "#0F766E"
    red = "#B91C1C"
    draw.rectangle((55, 55, 1445, 1845), outline="#A8BCC6", width=4)
    draw.text((750, 95), "SYNTHETIC DEMO - NOT A REAL PATIENT", fill=red, font=_font(30, bold=True), anchor="ma")
    draw.text((95, 175), "PATIENT INTAKE FORM", fill=navy, font=_font(50, bold=True))
    draw.line((95, 245, 1405, 245), fill=teal, width=6)
    rows = [
        ("Patient name", "Jordan Lee" if not degraded else "Avery Singh"),
        ("Patient ID", "SYN-2002" if not degraded else "SYN-3003"),
        ("Date of birth", "1957-11-03" if not degraded else "1979-02-14"),
        ("Encounter date", "2026-08-14" if not degraded else "2026-08-15"),
        ("Drug allergies", "Penicillin - rash" if not degraded else "Sulfa? handwriting unclear"),
        ("Current medication", "Metoprolol 50 mg by mouth twice daily" if not degraded else "Medication list attached"),
        ("Primary concern", "Post-discharge medication and lab review" if not degraded else "Follow-up request"),
    ]
    y = 305
    for label, value in rows:
        draw.rounded_rectangle((95, y, 1405, y + 150), radius=14, fill="#F7FAFC", outline="#C7DADF", width=3)
        draw.text((125, y + 22), label.upper(), fill=teal, font=_font(24, bold=True))
        draw.text((125, y + 69), value, fill=navy, font=_font(31))
        y += 180
    draw.text((95, 1610), "Patient-reported information; verification pending.", fill="#5B7082", font=_font(25))
    draw.text((95, 1695), "Signature: SYNTHETIC SAMPLE", fill=navy, font=_font(27, bold=True))
    if degraded:
        image = ImageEnhance.Contrast(image).enhance(0.45)
        image = image.filter(ImageFilter.GaussianBlur(radius=2.2))
        overlay = Image.new("RGBA", image.size, (232, 230, 216, 70))
        image = Image.alpha_composite(image.convert("RGBA"), overlay).convert("RGB")
    image.save(path, optimize=True)


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.strip() + "\n", encoding="utf-8")


def main() -> None:
    case_a = DATA_ROOT / "case_a_routine"
    case_b = DATA_ROOT / "case_b_review_now"
    case_c = DATA_ROOT / "case_c_degraded"

    create_clinical_pdf(
        case_a / "discharge_summary.pdf",
        "Discharge Summary",
        [
            ("Patient", "Maya Chen"),
            ("Patient ID", "SYN-1001"),
            ("Date of birth", "1968-04-12"),
            ("Facility", "North Valley Medical Center"),
            ("Encounter", "2026-08-10 to 2026-08-12"),
        ],
        [
            ("Discharge diagnoses", ["Community-acquired pneumonia, improving.", "Hypertension, stable."]),
            ("Allergies", ["No known drug allergies (NKDA)."]) ,
            ("Discharge medications", ["Azithromycin 250 mg by mouth once daily for 4 days - new.", "Lisinopril 10 mg by mouth once daily - active."]),
            ("Follow-up", ["Primary care appointment with Dr. Nair is scheduled for 2026-08-19."]),
            ("Disposition", ["Discharged home in stable condition. No pending tests documented."]),
        ],
    )
    create_clinical_pdf(
        case_a / "lab_report.pdf",
        "Laboratory Report",
        [
            ("Patient", "Maya Chen"),
            ("Patient ID", "SYN-1001"),
            ("Date of birth", "1968-04-12"),
            ("Collected", "2026-08-12 07:10"),
        ],
        [
            ("Results", ["White blood cell count: 8.4 x10^9/L (reference 4.0-11.0) - normal.", "Potassium: 4.2 mmol/L (reference 3.5-5.1) - normal.", "Creatinine: 0.9 mg/dL (reference 0.6-1.2) - normal."]),
            ("Comment", ["No critical or abnormal results are flagged on this report."]),
        ],
    )
    write_text(
        case_a / "physician_note.txt",
        """
SYNTHETIC DEMO - NOT A REAL PATIENT
Physician follow-up note
Patient: Maya Chen | Patient ID: SYN-1001 | DOB: 1968-04-12
Encounter date: 2026-08-12 | North Valley Medical Center

Community-acquired pneumonia is improving. Hypertension is stable.
Medication reconciliation: azithromycin 250 mg by mouth once daily for 4 days is new;
lisinopril 10 mg by mouth once daily remains active. No known drug allergies.
Primary care follow-up with Dr. Nair is scheduled for 2026-08-19.
No pending tests or urgent alerts are documented.
        """,
    )

    create_clinical_pdf(
        case_b / "discharge_summary.pdf",
        "Discharge Summary",
        [
            ("Patient", "Jordan Lee"),
            ("Patient ID", "SYN-2002"),
            ("Date of birth", "1957-11-03"),
            ("Facility", "North Valley Medical Center"),
            ("Encounter", "2026-08-13 to 2026-08-14"),
        ],
        [
            ("Discharge diagnoses", ["Atrial fibrillation, current.", "Hypertension, current."]),
            ("Allergies", ["No known drug allergies (NKDA)."]) ,
            ("Medications", ["Metoprolol 25 mg by mouth twice daily - active."]),
            ("Critical result", ["CRITICAL RESULT: Potassium 6.2 mmol/L. Urgent clinician review is required."]),
            ("Pending items", ["Repeat potassium test is pending."]),
            ("Follow-up", ["Primary care follow-up is recommended within one week; appointment is not yet scheduled."]),
        ],
    )
    create_clinical_pdf(
        case_b / "lab_report.pdf",
        "Laboratory Report",
        [
            ("Patient", "Jordan Lee"),
            ("Patient ID", "SYN-2002"),
            ("Date of birth", "1957-11-03"),
            ("Collected", "2026-08-14 09:35"),
        ],
        [
            ("Results", ["Potassium: 6.2 mmol/L (reference 3.5-5.1) - CRITICAL HIGH.", "Creatinine: 1.1 mg/dL (reference 0.6-1.2) - normal."]),
            ("Alert", ["Critical result notification: urgent clinician review required. Repeat potassium is pending."]),
        ],
    )
    write_text(
        case_b / "progress_note.txt",
        """
SYNTHETIC DEMO - NOT A REAL PATIENT
Progress note
Patient: Jordan Lee | Patient ID: SYN-2002 | DOB: 1957-11-03
Encounter date: 2026-08-14 | North Valley Medical Center

Allergy list: Penicillin - rash (confirmed).
Medication list: Metoprolol 50 mg by mouth twice daily - changed dose.
Potassium 6.2 mmol/L is documented as a critical result. Urgent clinician review required.
Repeat potassium test remains pending.
Cardiology follow-up is pending; provider is cardiology and the appointment date is not specified.
        """,
    )
    create_intake_image(case_b / "intake_form.png")
    create_intake_image(case_c / "degraded_intake.png", degraded=True)

    manifest = {
        "dataset_notice": "All records are fictional and contain no real patient data.",
        "cases": {
            "case_a": {
                "label": "Routine transition - consistent records",
                "description": "Three consistent documents with a scheduled follow-up and no source-labelled alerts.",
                "files": [
                    "sample_data/case_a_routine/discharge_summary.pdf",
                    "sample_data/case_a_routine/lab_report.pdf",
                    "sample_data/case_a_routine/physician_note.txt",
                ],
                "golden": "sample_data/golden/case_a_expected.json",
                "show_in_app": True,
            },
            "case_b": {
                "label": "Review now - conflicts and critical result",
                "description": "Four documents with an explicit critical lab, allergy conflict, dose discrepancy, and pending follow-up.",
                "files": [
                    "sample_data/case_b_review_now/discharge_summary.pdf",
                    "sample_data/case_b_review_now/lab_report.pdf",
                    "sample_data/case_b_review_now/progress_note.txt",
                    "sample_data/case_b_review_now/intake_form.png",
                ],
                "golden": "sample_data/golden/case_b_expected.json",
                "show_in_app": True,
            },
            "case_c": {
                "label": "Degraded image - uncertainty handling",
                "description": "A deliberately low-contrast scan used to validate cautious extraction behavior.",
                "files": ["sample_data/case_c_degraded/degraded_intake.png"],
                "golden": "sample_data/golden/case_c_expected.json",
                "show_in_app": False,
            },
        },
    }
    (DATA_ROOT / "manifest.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8"
    )
    golden = DATA_ROOT / "golden"
    golden.mkdir(parents=True, exist_ok=True)
    (golden / "case_a_expected.json").write_text(
        json.dumps(
            {
                "priority": "ROUTINE",
                "required_values": ["Maya Chen", "SYN-1001", "Azithromycin", "Lisinopril", "2026-08-19"],
                "required_rules": [],
                "forbidden_rules": ["IDENTITY_MISMATCH", "ALLERGY_RECORD_CONFLICT", "SOURCE_CRITICAL_LAB"],
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    (golden / "case_b_expected.json").write_text(
        json.dumps(
            {
                "priority": "REVIEW NOW",
                "required_values": ["Jordan Lee", "SYN-2002", "Penicillin", "Metoprolol", "6.2"],
                "required_rules": ["ALLERGY_RECORD_CONFLICT", "MEDICATION_RECONCILIATION", "SOURCE_CRITICAL_LAB", "FOLLOW_UP_INCOMPLETE", "PENDING_ITEM"],
                "forbidden_rules": ["IDENTITY_MISMATCH"],
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    (golden / "case_c_expected.json").write_text(
        json.dumps(
            {
                "behavior": "Do not assign high confidence to image-only facts without corroboration.",
                "max_confidence": "medium",
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"Generated synthetic dataset under {DATA_ROOT}")


if __name__ == "__main__":
    main()

