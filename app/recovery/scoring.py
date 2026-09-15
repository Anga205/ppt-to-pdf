"""Stage 12: Recovery scoring and selection."""
import logging
from pathlib import Path
from typing import List, Dict


def score_pdf(pdf_path: Path, expected_slides: int = 0) -> Dict:
    score = {"exists": False, "size": 0, "pages": 0, "readable": False, "score": 0}
    if not pdf_path.exists():
        return score
    score["exists"] = True
    score["size"] = pdf_path.stat().st_size
    try:
        # Try to read page count with PyPDF2 or pypdf
        try:
            from pypdf import PdfReader
            reader = PdfReader(str(pdf_path))
            score["pages"] = len(reader.pages)
            score["readable"] = True
        except Exception:
            pass
    except Exception:
        pass
    # Simple scoring
    if score["exists"] and score["readable"]:
        score["score"] = 100
        if expected_slides > 0 and score["pages"] < expected_slides:
            score["score"] = max(50, 100 - (expected_slides - score["pages"]) * 10)
    elif score["exists"]:
        score["score"] = 30
    return score
