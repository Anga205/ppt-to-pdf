import logging
import tempfile
from pathlib import Path

from app.concurrency import get_limiter
from app.services.libreoffice_converter import convert_with_libreoffice_writer
from app.recovery.document_pipeline import run_document_recovery


def convert_document_file(input_path: Path, pdf_path: Path):
    with get_limiter().slot():
        return _convert_document_unlimited(input_path, pdf_path)


def _convert_document_unlimited(input_path: Path, pdf_path: Path):
    try:
        report = run_document_recovery(input_path, pdf_path)
        if report.successful_strategy:
            return pdf_path
    except Exception as exc:
        logging.info("Document recovery pipeline failed: %s", exc)
    if convert_with_libreoffice_writer(input_path, pdf_path):
        return pdf_path
    raise RuntimeError("Document conversion failed")
