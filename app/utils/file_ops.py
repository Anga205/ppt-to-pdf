import shutil
from pathlib import Path


def file_has_content(path: Path):
    return path.exists() and path.is_file() and path.stat().st_size > 0


def move_pdf_if_valid(candidate_pdf: Path, target_pdf: Path):
    if not file_has_content(candidate_pdf):
        return False

    target_pdf.parent.mkdir(parents=True, exist_ok=True)
    if target_pdf.exists():
        target_pdf.unlink()

    shutil.move(str(candidate_pdf), str(target_pdf))
    return file_has_content(target_pdf)


def copy_stream_to_path(source_stream, target_path: Path):
    target_path.parent.mkdir(parents=True, exist_ok=True)
    with open(target_path, "wb") as destination:
        shutil.copyfileobj(source_stream, destination)


def read_file_bytes(path: Path):
    with open(path, "rb") as source:
        return source.read()
