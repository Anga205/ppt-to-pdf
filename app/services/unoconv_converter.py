import logging
import shutil
from pathlib import Path

from app.utils.command_runner import run_command
from app.utils.file_ops import move_pdf_if_valid


def convert_with_unoconv(input_path: Path, pdf_path: Path):
    unoconv_bin = shutil.which("unoconv")
    if not unoconv_bin:
        logging.info("unoconv not found, skipping")
        return False

    generated_pdf = input_path.with_suffix(".pdf")
    if generated_pdf.exists():
        generated_pdf.unlink()

    command = [unoconv_bin, "-f", "pdf", str(input_path)]
    success, _ = run_command(command)
    if success and move_pdf_if_valid(generated_pdf, pdf_path):
        logging.info("unoconv conversion succeeded")
        return True

    logging.error("unoconv conversion failed")
    return False
