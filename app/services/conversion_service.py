import logging
import shutil
import tempfile
from pathlib import Path

from app.services.libreoffice_converter import (
    convert_with_libreoffice,
    convert_with_libreoffice_generic_only,
)
from app.services.repair_utils import (
    detect_container,
    list_pptx_repair_candidates,
)


def _retry_after_all_pptx_repairs(input_path: Path, pdf_path: Path):
    with tempfile.TemporaryDirectory() as temp_dir_name:
        repair_dir = Path(temp_dir_name) / "repairs"
        repair_dir.mkdir(parents=True, exist_ok=True)
        candidates = list_pptx_repair_candidates(input_path, repair_dir)
        for candidate in candidates:
            logging.info("Retrying conversion with repaired file: %s", candidate.name)
            if convert_with_libreoffice(candidate, pdf_path):
                return True
    return False


def _retry_legacy_ole_methods(input_path: Path, pdf_path: Path):
    if detect_container(input_path) != "ole":
        return False

    logging.info("Detected OLE container, attempting legacy PPT conversion")
    with tempfile.TemporaryDirectory() as temp_dir_name:
        legacy_dir = Path(temp_dir_name) / "legacy"
        legacy_dir.mkdir(parents=True, exist_ok=True)
        ppt_input = legacy_dir / "in.ppt"
        pptx_input = legacy_dir / "in.pptx"
        shutil.copy2(input_path, ppt_input)
        if convert_with_libreoffice_generic_only(ppt_input, pdf_path):
            return True
        shutil.copy2(input_path, pptx_input)
        return convert_with_libreoffice(pptx_input, pdf_path)


def _retry_extension_variants(input_path: Path, pdf_path: Path):
    with tempfile.TemporaryDirectory() as temp_dir_name:
        variant_dir = Path(temp_dir_name) / "variants"
        variant_dir.mkdir(parents=True, exist_ok=True)
        for suffix in (".pptx", ".ppt"):
            variant_input = variant_dir / f"in{suffix}"
            shutil.copy2(input_path, variant_input)
            if convert_with_libreoffice(variant_input, pdf_path):
                return True
    return False


def convert_file(input_path: Path, pdf_path: Path):
    logging.info("Starting conversion for %s", input_path)
    if convert_with_libreoffice(input_path, pdf_path):
        return pdf_path
    if _retry_after_all_pptx_repairs(input_path, pdf_path):
        return pdf_path
    if _retry_legacy_ole_methods(input_path, pdf_path):
        return pdf_path
    if _retry_extension_variants(input_path, pdf_path):
        return pdf_path
    logging.error("Conversion failed after all fallback strategies")
    raise RuntimeError("Conversion failed")
