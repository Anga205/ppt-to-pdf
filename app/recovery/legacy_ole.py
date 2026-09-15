"""Stage 8: Legacy .ppt OLE deep repair."""
import logging
from pathlib import Path


def inspect_ole_streams(input_path: Path) -> dict:
    try:
        import olefile
        ole = olefile.OleFileIO(str(input_path))
        streams = ole.listdir()
        ole.close()
        return {"streams": streams, "has_powerpoint_document": any("PowerPoint Document" in s for s in streams)}
    except Exception as exc:
        logging.info("OLE inspection failed: %s", exc)
        return {"streams": [], "has_powerpoint_document": False}
