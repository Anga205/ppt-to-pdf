"""Stage 13-14: Logging, diagnostics, safety, resource limits."""
import logging
import os
import tempfile
from pathlib import Path

logger = logging.getLogger(__name__)


def safe_temp_dir(prefix="ppt-recovery-") -> Path:
    """Return a temp dir on the large storage volume when configured.

    On low-memory devices (e.g. Android) /tmp may be small. The base directory
    can be overridden with RECOVERY_TEMP_DIR or TMPDIR.
    """
    base = os.getenv("RECOVERY_TEMP_DIR") or os.getenv("TMPDIR") or tempfile.gettempdir()
    base_path = Path(base)
    try:
        base_path.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        logger.warning("Could not create temp base %s: %s", base_path, exc)
        base_path = Path(tempfile.gettempdir())
    return Path(tempfile.mkdtemp(prefix=prefix, dir=str(base_path)))
