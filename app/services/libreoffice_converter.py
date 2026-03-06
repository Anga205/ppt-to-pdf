import logging
import shutil
import tempfile
from pathlib import Path

from app.constants import ALLOWED_EXTENSIONS, LIBREOFFICE_CANDIDATES, LIBREOFFICE_FLAGS
from app.utils.command_runner import find_first_binary, run_command
from app.utils.file_ops import file_has_content, move_pdf_if_valid


def _find_libreoffice_binary():
    libreoffice_bin = find_first_binary(LIBREOFFICE_CANDIDATES)
    if libreoffice_bin:
        logging.info("Found LibreOffice executable: %s", libreoffice_bin)
        return libreoffice_bin
    logging.error("LibreOffice executable not found (soffice/libreoffice)")
    return None


def _build_libreoffice_command(libreoffice_bin, profile_dir, convert_to, out_dir, input_path):
    return [
        libreoffice_bin,
        *LIBREOFFICE_FLAGS,
        f"-env:UserInstallation={profile_dir.as_uri()}",
        "--convert-to",
        convert_to,
        "--outdir",
        str(out_dir),
        str(input_path),
    ]


def _run_libreoffice_convert(libreoffice_bin, input_path, out_dir, convert_to, expected_suffix, work_dir):
    out_dir.mkdir(parents=True, exist_ok=True)
    profile_dir = Path(tempfile.mkdtemp(prefix="lo-profile-", dir=str(work_dir)))
    command = _build_libreoffice_command(
        libreoffice_bin,
        profile_dir,
        convert_to,
        out_dir,
        input_path,
    )
    success, _ = run_command(command)
    output_candidate = out_dir / f"{input_path.stem}{expected_suffix}"
    if success and file_has_content(output_candidate):
        return output_candidate
    return None


def _attempt_pdf_strategy(libreoffice_bin, input_path, pdf_path, convert_to, out_dir, step_name, work_dir):
    generated_pdf = _run_libreoffice_convert(
        libreoffice_bin,
        input_path,
        out_dir,
        convert_to,
        ".pdf",
        work_dir,
    )
    if generated_pdf and move_pdf_if_valid(generated_pdf, pdf_path):
        logging.info("LibreOffice %s succeeded", step_name)
        return True
    return False


def _prepare_short_input_path(input_path, temp_dir):
    short_dir = temp_dir / "temp"
    short_dir.mkdir(parents=True, exist_ok=True)
    suffix = input_path.suffix.lower()
    short_suffix = suffix if suffix in ALLOWED_EXTENSIONS else ".pptx"
    short_input = short_dir / f"in{short_suffix}"
    shutil.copy2(input_path, short_input)
    return short_input


def _strategy_short_path_retry(libreoffice_bin, input_path, pdf_path, temp_dir):
    short_input = _prepare_short_input_path(input_path, temp_dir)
    if _attempt_pdf_strategy(
        libreoffice_bin,
        short_input,
        pdf_path,
        "pdf:impress_pdf_Export",
        temp_dir / "s331-short-impress",
        "strategy 3.3 (impress filter)",
        temp_dir,
    ):
        return True
    return _attempt_pdf_strategy(
        libreoffice_bin,
        short_input,
        pdf_path,
        "pdf",
        temp_dir / "s332-short-generic",
        "strategy 3.3 (generic)",
        temp_dir,
    )


def _strategy_two_step_conversion(libreoffice_bin, input_path, pdf_path, temp_dir):
    generated_odp = _run_libreoffice_convert(
        libreoffice_bin,
        input_path,
        temp_dir / "s341-odp",
        "odp",
        ".odp",
        temp_dir,
    )
    if not generated_odp:
        return False

    generated_pdf = _run_libreoffice_convert(
        libreoffice_bin,
        generated_odp,
        temp_dir / "s342-pdf",
        "pdf",
        ".pdf",
        temp_dir,
    )
    if generated_pdf and move_pdf_if_valid(generated_pdf, pdf_path):
        logging.info("LibreOffice strategy 3.4 succeeded")
        return True
    return False


def _run_libreoffice_strategies(libreoffice_bin, input_path, pdf_path, temp_dir):
    if _attempt_pdf_strategy(
        libreoffice_bin,
        input_path,
        pdf_path,
        "pdf:impress_pdf_Export",
        temp_dir / "s31-impress",
        "strategy 3.1",
        temp_dir,
    ):
        return True
    if _attempt_pdf_strategy(
        libreoffice_bin,
        input_path,
        pdf_path,
        "pdf",
        temp_dir / "s32-generic",
        "strategy 3.2",
        temp_dir,
    ):
        return True
    if _strategy_short_path_retry(libreoffice_bin, input_path, pdf_path, temp_dir):
        return True
    return _strategy_two_step_conversion(libreoffice_bin, input_path, pdf_path, temp_dir)


def convert_with_libreoffice(input_path: Path, pdf_path: Path):
    libreoffice_bin = _find_libreoffice_binary()
    if not libreoffice_bin:
        return False

    with tempfile.TemporaryDirectory() as temp_dir_name:
        temp_dir = Path(temp_dir_name)
        if _run_libreoffice_strategies(libreoffice_bin, input_path, pdf_path, temp_dir):
            return True

    logging.error("LibreOffice conversion failed for all strategies")
    return False


def convert_with_libreoffice_generic_only(input_path: Path, pdf_path: Path):
    libreoffice_bin = _find_libreoffice_binary()
    if not libreoffice_bin:
        return False

    with tempfile.TemporaryDirectory() as temp_dir_name:
        temp_dir = Path(temp_dir_name)
        return _attempt_pdf_strategy(
            libreoffice_bin,
            input_path,
            pdf_path,
            "pdf",
            temp_dir / "legacy-generic-pdf",
            "legacy generic conversion",
            temp_dir,
        )
