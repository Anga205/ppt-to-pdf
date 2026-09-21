"""Stage 8: Legacy .doc OLE deep inspection."""
import logging
from pathlib import Path


def inspect_document_ole(input_path: Path) -> dict:
    try:
        import olefile
        ole = olefile.OleFileIO(str(input_path))
        streams = ole.listdir()
        ole.close()
        return {
            "streams": streams,
            "has_word_document": any("WordDocument" in s for s in streams),
        }
    except Exception as exc:
        logging.info("OLE inspection failed: %s", exc)
        return {"streams": [], "has_word_document": False}
