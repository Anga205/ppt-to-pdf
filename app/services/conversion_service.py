import logging
import shutil
import tempfile
from pathlib import Path

from app.services.libreoffice_converter import (
    convert_with_libreoffice,
    convert_with_libreoffice_generic_only,
)
from app.services.powerpoint_com import convert_with_powerpoint_com
from app.services.repair_utils import detect_container, repair_pptx_zip
from app.services.unoconv_converter import convert_with_unoconv


def _retry_after_zip_repair(input_path: Path, pdf_path: Path):
    with tempfile.TemporaryDirectory() as temp_dir_name:
        temp_dir = Path(temp_dir_name)
        repaired_path = temp_dir / f"repaired{input_path.suffix.lower() or '.pptx'}"
        if not repair_pptx_zip(input_path, repaired_path):
            return False
        return convert_with_libreoffice(repaired_path, pdf_path)


def _retry_legacy_ole_path(input_path: Path, pdf_path: Path):
    if detect_container(input_path) != "ole":
        return False

    logging.info("Detected OLE container, attempting legacy PPT conversion")
    with tempfile.TemporaryDirectory() as temp_dir_name:
        legacy_dir = Path(temp_dir_name) / "temp"
        legacy_dir.mkdir(parents=True, exist_ok=True)
        legacy_input = legacy_dir / "in.ppt"
        shutil.copy2(input_path, legacy_input)
        return convert_with_libreoffice_generic_only(legacy_input, pdf_path)


def convert_file(input_path: Path, pdf_path: Path):
    logging.info("Starting conversion for %s", input_path)
    if convert_with_powerpoint_com(input_path, pdf_path):
        return pdf_path
    if convert_with_unoconv(input_path, pdf_path):
        return pdf_path
    if convert_with_libreoffice(input_path, pdf_path):
        return pdf_path
    if _retry_after_zip_repair(input_path, pdf_path):
        return pdf_path
    if _retry_legacy_ole_path(input_path, pdf_path):
        return pdf_path
    logging.error("Conversion failed after all fallback strategies")
    raise RuntimeError("Conversion failed")
