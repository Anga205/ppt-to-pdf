"""Stage 11: Last-resort PDF reconstruction from document content."""
import logging
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET


def reconstruct_document_pdf(input_path: Path, pdf_path: Path) -> bool:
    try:
        texts = []
        with zipfile.ZipFile(str(input_path), "r") as zf:
            for name in sorted(zf.namelist()):
                if name == "word/document.xml":
                    try:
                        xml = zf.read(name).decode("utf-8", errors="ignore")
                        root = ET.fromstring(xml)
                        text = " ".join(el.text or "" for el in root.iter() if el.text)
                        texts.append(text)
                    except Exception:
                        texts.append("")
        if not texts:
            texts = ["Document content could not be fully recovered."]
        try:
            from weasyprint import HTML
            body = "".join(
                f"<div style='page-break-after:always;padding:40px;font-family:sans-serif;'>"
                f"<p style='white-space:pre-wrap;'>{_esc(t)}</p></div>"
                for t in texts
            )
            HTML(string=f"<html><body>{body}</body></html>").write_pdf(str(pdf_path))
            return pdf_path.exists() and pdf_path.stat().st_size > 0
        except Exception as exc:
            logging.info("Weasyprint reconstruction failed: %s", exc)
        # Fallback: reportlab
        try:
            from reportlab.lib.pagesizes import letter
            from reportlab.pdfgen import canvas
            c = canvas.Canvas(str(pdf_path), pagesize=letter)
            width, height = letter
            for text in texts:
                c.setFont("Helvetica", 12)
                y = height - 60
                for line in (text or "").splitlines() or [""]:
                    c.drawString(40, y, line[:100])
                    y -= 14
                c.showPage()
            c.save()
            return pdf_path.exists() and pdf_path.stat().st_size > 0
        except Exception as exc:
            logging.info("Reportlab reconstruction failed: %s", exc)
        return False
    except Exception as exc:
        logging.error("Document reconstruction failed: %s", exc)
        return False


def _esc(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
