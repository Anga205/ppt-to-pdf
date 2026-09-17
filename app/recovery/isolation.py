"""Stage 5: Progressive isolation — remove problematic components."""
import logging, zipfile, tempfile
from pathlib import Path

def progressive_isolation(input_path: Path, repaired_path: Path) -> bool:
    try:
        with tempfile.TemporaryDirectory() as td:
            extract_dir = Path(td) / "extracted"
            extract_dir.mkdir()
            with zipfile.ZipFile(str(input_path), "r") as zf:
                zf.extractall(str(extract_dir))
            changed = False
            for p in extract_dir.rglob("ppt/embeddings/*"):
                if p.is_file(): p.unlink(); changed = True
            for p in extract_dir.rglob("ppt/oleObjects/*"):
                if p.is_file(): p.unlink(); changed = True
            if changed:
                repaired_path.parent.mkdir(parents=True, exist_ok=True)
                with zipfile.ZipFile(str(repaired_path), "w", compression=zipfile.ZIP_DEFLATED) as zf:
                    for file_path in extract_dir.rglob("*"):
                        if file_path.is_file():
                            zf.write(str(file_path), file_path.relative_to(extract_dir).as_posix())
                return repaired_path.exists() and repaired_path.stat().st_size > 0
            return False
    except Exception as exc:
        logging.error("Progressive isolation failed: %s", exc)
        return False
