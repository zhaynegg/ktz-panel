"""Russian-capable PDF summary export using ReportLab and system fonts."""

from __future__ import annotations

from io import BytesIO
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

_FONT_REGISTERED = False
_FONT_NAME = "Helvetica"


def _ensure_font() -> str:
    global _FONT_REGISTERED, _FONT_NAME
    if _FONT_REGISTERED:
        return _FONT_NAME

    candidates = [
        Path("C:/Windows/Fonts/arial.ttf"),
        Path("C:/Windows/Fonts/calibri.ttf"),
        Path("C:/Windows/Fonts/verdana.ttf"),
    ]
    for font_path in candidates:
        if font_path.exists():
            pdfmetrics.registerFont(TTFont("KztReportFont", str(font_path)))
            _FONT_NAME = "KztReportFont"
            _FONT_REGISTERED = True
            return _FONT_NAME

    _FONT_REGISTERED = True
    return _FONT_NAME


def build_summary_pdf(lines: list[str], title: str = "KZT Digital Twin Summary") -> bytes:
    """Generate a readable PDF with Cyrillic support and simple section hierarchy."""
    font_name = _ensure_font()
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=16 * mm,
        bottomMargin=16 * mm,
        title=title,
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "KztTitle",
        parent=styles["Title"],
        fontName=font_name,
        fontSize=18,
        leading=22,
        textColor=colors.HexColor("#0f2740"),
        alignment=TA_LEFT,
        spaceAfter=10,
    )
    heading_style = ParagraphStyle(
        "KztHeading",
        parent=styles["Heading3"],
        fontName=font_name,
        fontSize=12,
        leading=16,
        textColor=colors.HexColor("#1b4b7a"),
        spaceBefore=8,
        spaceAfter=4,
    )
    body_style = ParagraphStyle(
        "KztBody",
        parent=styles["BodyText"],
        fontName=font_name,
        fontSize=10.5,
        leading=14,
        textColor=colors.HexColor("#1a1a18"),
        spaceAfter=2,
    )

    story = [Paragraph(title, title_style), Spacer(1, 2 * mm)]
    for raw_line in lines:
        line = raw_line.strip()
        if not line:
            story.append(Spacer(1, 2.5 * mm))
            continue

        if line.endswith(":") and not line.startswith("- "):
            story.append(Paragraph(line, heading_style))
            continue

        if line.startswith("- "):
            story.append(Paragraph(f"• {line[2:]}", body_style))
            continue

        story.append(Paragraph(line, body_style))

    doc.build(story)
    return buffer.getvalue()
