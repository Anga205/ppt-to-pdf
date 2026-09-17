"""Stage 7: Slide reconstruction from XML when rendering fails."""
import logging
import zipfile
import tempfile
from pathlib import Path
from xml.etree import ElementTree as ET


def reconstruct_slides_to_pdf(input_path: Path, pdf_path: Path) -> bool:
    """Reconstruct slides from XML text/images when native rendering fails."""
    try:
        texts = []
        with zipfile.ZipFile(str(input_path), "r") as zf:
            for name in sorted(zf.namelist()):
                if name.startswith("ppt/slides/slide") and name.endswith(".xml") and not name.endswith("_rels/"):
                    try:
                        xml = zf.read(name).decode("utf-8", errors="ignore")
                        root = ET.fromstring(xml)
                        slide_text = " ".join(
                            el.text or "" for el in root.iter() if el.tag.endswith("}t") or el.tag == "t"
                        )
                        texts.append(slide_text)
                    except Exception:
                        texts.append("")
        if not texts:
            texts = ["Presentation content could not be fully recovered."]
        # Use weasyprint to build PDF from reconstructed text
        from weasyprint import HTML
        body = "".join(
            f"<div style='page-break-after:always;padding:40px;font-family:sans-serif;'>"
            f"<h2>Slide {i+1}</h2><p style='white-space:pre-wrap;'>{_esc(t)}</p></div>"
            for i, t in enumerate(texts)
        )
        HTML(string=f"<html><body>{body}</body></html>").write_pdf(str(pdf_path))
        return pdf_path.exists() and pdf_path.stat().st_size > 0
    except Exception as exc:
        logging.error("Slide reconstruction failed: %s", exc)
        return False


def _esc(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
