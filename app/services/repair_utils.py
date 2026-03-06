import logging
import shutil
import tempfile
import zipfile
from pathlib import Path

from app.constants import JUNK_BASENAMES, OLE_HEADER, ZIP_HEADER
from app.utils.file_ops import file_has_content


def detect_container(input_path: Path):
    with open(input_path, "rb") as source:
        header = source.read(8)
    if len(header) >= 4 and header[:4] == ZIP_HEADER:
        return "zip"
    if len(header) == 8 and header == OLE_HEADER:
        return "ole"
    return "unknown"


def _member_parts(member_name):
    normalized = member_name.replace("\\", "/").strip("/")
    return [part for part in normalized.split("/") if part and part != "."]


def _is_junk_member(parts):
    if not parts:
        return True
    basename = parts[-1]
    if "__MACOSX" in parts:
        return True
    if basename in JUNK_BASENAMES:
        return True
    return basename.startswith("._")


def _extract_member(archive, member, extracted_dir):
    parts = _member_parts(member.filename)
    if _is_junk_member(parts):
        return
    target_path = extracted_dir.joinpath(*parts)
    if member.is_dir():
        target_path.mkdir(parents=True, exist_ok=True)
        return
    target_path.parent.mkdir(parents=True, exist_ok=True)
    with archive.open(member, "r") as src, open(target_path, "wb") as dst:
        shutil.copyfileobj(src, dst)


def _extract_non_junk_members(input_path, extracted_dir):
    with zipfile.ZipFile(input_path, "r") as archive:
        for member in archive.infolist():
            _extract_member(archive, member, extracted_dir)


def _repack_zip(extracted_dir, repaired_path):
    repaired_path.parent.mkdir(parents=True, exist_ok=True)
    file_count = 0
    with zipfile.ZipFile(repaired_path, "w", compression=zipfile.ZIP_DEFLATED) as repaired:
        for disk_file in sorted(extracted_dir.rglob("*")):
            if not disk_file.is_file():
                continue
            arcname = disk_file.relative_to(extracted_dir).as_posix()
            repaired.write(disk_file, arcname=arcname)
            file_count += 1
    return file_count


def repair_pptx_zip(input_path: Path, repaired_path: Path):
    if not zipfile.is_zipfile(input_path):
        logging.info("Input is not a ZIP archive, skipping PPTX repair")
        return False

    logging.info("Attempting PPTX ZIP repair")
    with tempfile.TemporaryDirectory() as temp_dir_name:
        extracted_dir = Path(temp_dir_name) / "extracted"
        extracted_dir.mkdir(parents=True, exist_ok=True)
        _extract_non_junk_members(input_path, extracted_dir)
        file_count = _repack_zip(extracted_dir, repaired_path)

    if file_count == 0:
        logging.error("ZIP repair produced no files")
        return False
    logging.info("PPTX ZIP repair created %s entries", file_count)
    return file_has_content(repaired_path)
