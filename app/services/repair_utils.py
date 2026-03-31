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


def is_zip_container(input_path: Path):
    return zipfile.is_zipfile(input_path)


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


def _drop_root_prefix(parts, prefix):
    if not prefix:
        return parts
    if parts[: len(prefix)] == prefix:
        return parts[len(prefix) :]
    return parts


def _collect_member_parts(input_path):
    members = []
    with zipfile.ZipFile(input_path, "r") as archive:
        for member in archive.infolist():
            parts = _member_parts(member.filename)
            if parts:
                members.append(parts)
    return members


def _find_flatten_prefix(member_parts):
    if not member_parts:
        return []
    first = member_parts[0]
    if len(first) < 2:
        return []
    prefix = [first[0]]
    for parts in member_parts:
        if len(parts) < 2 or parts[0] != prefix[0]:
            return []
    return prefix


def _extract_member(archive, member, extracted_dir, drop_prefix=None):
    parts = _member_parts(member.filename)
    parts = _drop_root_prefix(parts, drop_prefix or [])
    if _is_junk_member(parts):
        return
    target_path = extracted_dir.joinpath(*parts)
    if member.is_dir():
        target_path.mkdir(parents=True, exist_ok=True)
        return
    target_path.parent.mkdir(parents=True, exist_ok=True)
    with archive.open(member, "r") as src, open(target_path, "wb") as dst:
        shutil.copyfileobj(src, dst)


def _extract_non_junk_members(input_path, extracted_dir, drop_prefix=None):
    with zipfile.ZipFile(input_path, "r") as archive:
        for member in archive.infolist():
            _extract_member(archive, member, extracted_dir, drop_prefix=drop_prefix)


def _repack_zip(extracted_dir, repaired_path, compression):
    repaired_path.parent.mkdir(parents=True, exist_ok=True)
    file_count = 0
    with zipfile.ZipFile(repaired_path, "w", compression=compression) as repaired:
        for disk_file in sorted(extracted_dir.rglob("*")):
            if not disk_file.is_file():
                continue
            arcname = disk_file.relative_to(extracted_dir).as_posix()
            repaired.write(disk_file, arcname=arcname)
            file_count += 1
    return file_count


def _repair_with_options(input_path, repaired_path, compression, drop_prefix=None):
    with tempfile.TemporaryDirectory() as temp_dir_name:
        extracted_dir = Path(temp_dir_name) / "extracted"
        extracted_dir.mkdir(parents=True, exist_ok=True)
        _extract_non_junk_members(input_path, extracted_dir, drop_prefix=drop_prefix)
        file_count = _repack_zip(extracted_dir, repaired_path, compression)
    if file_count == 0:
        logging.error("ZIP repair produced no files")
        return False
    return file_has_content(repaired_path)


def repair_pptx_zip(input_path: Path, repaired_path: Path):
    if not zipfile.is_zipfile(input_path):
        logging.info("Input is not a ZIP archive, skipping PPTX repair")
        return False

    logging.info("Attempting PPTX ZIP repair")
    repaired = _repair_with_options(
        input_path,
        repaired_path,
        compression=zipfile.ZIP_DEFLATED,
    )
    if repaired:
        logging.info("PPTX ZIP clean repair succeeded")
    return repaired


def repair_pptx_zip_flatten_root(input_path: Path, repaired_path: Path):
    if not zipfile.is_zipfile(input_path):
        return False
    member_parts = _collect_member_parts(input_path)
    drop_prefix = _find_flatten_prefix(member_parts)
    if not drop_prefix:
        return False
    logging.info("Attempting PPTX root flatten repair")
    repaired = _repair_with_options(
        input_path,
        repaired_path,
        compression=zipfile.ZIP_DEFLATED,
        drop_prefix=drop_prefix,
    )
    if repaired:
        logging.info("PPTX flatten repair succeeded")
    return repaired


def repair_pptx_zip_store_only(input_path: Path, repaired_path: Path):
    if not zipfile.is_zipfile(input_path):
        return False
    logging.info("Attempting PPTX store-only repack repair")
    repaired = _repair_with_options(
        input_path,
        repaired_path,
        compression=zipfile.ZIP_STORED,
    )
    if repaired:
        logging.info("PPTX store-only repair succeeded")
    return repaired


def list_pptx_repair_candidates(input_path: Path, work_dir: Path):
    if not is_zip_container(input_path):
        return []

    methods = (
        ("clean", repair_pptx_zip),
        ("flatten", repair_pptx_zip_flatten_root),
        ("stored", repair_pptx_zip_store_only),
    )
    candidates = []
    for name, method in methods:
        candidate = work_dir / f"repair-{name}.pptx"
        try:
            if method(input_path, candidate):
                candidates.append(candidate)
        except Exception as exc:
            logging.error("Repair method %s failed: %s", name, exc)
    return candidates
