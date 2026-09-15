"""Stage 11: Last-resort PDF reconstruction from text/images."""
import logging
import tempfile
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET


def _extract_slide_texts(input_path: Path):
    """Extract text runs from each slide XML in a PPTX package."""
    slides = []
    try:
        with zipfile.ZipFile(str(input_path), "r") as zf:
            names = sorted(n for n in zf.namelist() if n.startswith("ppt/slides/slide") and n.endswith(".xml"))
            for name in names:
                try:
                    xml = zf.read(name).decode("utf-8", errors="ignore")
                    root = ET.fromstring(xml)
                    texts = []
                    for el in root.iter():
                        if el.tag.endswith("}t") and el.text:
                            texts.append(el.text)
                    slides.append(" ".join(texts))
                except Exception:
                    slides.append("")
    except Exception as exc:
        logging.warning("Could not extract slide text: %s", exc)
    return slides


def reconstruct_pdf_from_content(input_path: Path, pdf_path: Path) -> bool:
    slides = _extract_slide_texts(input_path)
    if not slides:
        slides = ["Content could not be recovered from this presentation."]

    # Try weasyprint first (best fidelity for text).
    try:
        from weasyprint import HTML
        body = "".join(
            f"<div style='page-break-after: always; padding: 40px; font-family: sans-serif;'>"
            f"<p style='white-space: pre-wrap;'>{_html_escape(text)}</p></div>"
            for text in slides
        )
        html_content = f"<html><body>{body}</body></html>"
        HTML(string=html_content).write_pdf(str(pdf_path))
        if pdf_path.exists() and pdf_path.stat().st_size > 0:
            return True
    except Exception as exc:
        logging.info("Weasyprint reconstruction failed: %s", exc)

    # Fallback: create a text PDF with reportlab.
    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.pdfgen import canvas
        c = canvas.Canvas(str(pdf_path), pagesize=letter)
        width, height = letter
        for text in slides:
            c.setFont("Helvetica", 12)
            y = height - 60
            for line in (text or "").splitlines() or [""]:
                if y < 60:
                    c.showPage()
                    c.setFont("Helvetica", 12)
                    y = height - 60
                c.drawString(60, y, line[:120])
                y -= 16
            c.showPage()
        c.save()
        return pdf_path.exists() and pdf_path.stat().st_size > 0
    except Exception as exc2:
        logging.info("Reportlab reconstruction failed: %s", exc2)
        return False


def _html_escape(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )
