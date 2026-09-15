"""Stage 4: python-pptx recovery attempt."""
import logging
from pathlib import Path


def try_python_pptx_repair(input_path: Path, repaired_path: Path) -> bool:
    try:
        from pptx import Presentation
        prs = Presentation(str(input_path))
        prs.save(str(repaired_path))
        return repaired_path.exists() and repaired_path.stat().st_size > 0
    except Exception as exc:
        logging.info("python-pptx repair failed: %s", exc)
        return False
