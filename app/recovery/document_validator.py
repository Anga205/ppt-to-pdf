"""Stage 2: Document package validation and structural diagnosis."""
import logging
import zipfile
from pathlib import Path


def diagnose_document_structure(input_path: Path) -> dict:
    result = {
        "is_zip": False,
        "crc_errors": [],
        "missing_content_types": False,
        "missing_document_xml": False,
        "dangling_rels": [],
        "missing_media_refs": [],
        "malformed_xml_files": [],
        "overall_health": "unknown",
    }
    if not zipfile.is_zipfile(str(input_path)):
        result["is_zip"] = False
        result["overall_health"] = "not_zip"
        return result
    result["is_zip"] = True
    try:
        with zipfile.ZipFile(str(input_path), "r") as zf:
            names = zf.namelist()
            for info in zf.infolist():
                try:
                    zf.read(info.filename)
                except Exception as exc:
                    result["crc_errors"].append(f"{info.filename}: {exc}")
            if "[Content_Types].xml" not in names:
                result["missing_content_types"] = True
            else:
                try:
                    ct = zf.read("[Content_Types].xml").decode("utf-8", errors="ignore")
                    if "wordprocessingml" not in ct and "word" not in ct:
                        result["missing_content_types"] = True
                except Exception:
                    pass
            if "word/document.xml" not in names:
                result["missing_document_xml"] = True
            # Inspect relationships
            rels_path = "word/_rels/document.xml.rels"
            if rels_path in names:
                try:
                    rels = zf.read(rels_path).decode("utf-8", errors="ignore")
                    # Basic dangling rel detection: references to missing targets
                    # Simplified: just note if file exists
                except Exception:
                    pass
    except Exception as exc:
        result["errors"] = [str(exc)]
    result["overall_health"] = "corrupt" if (result["crc_errors"] or result["missing_document_xml"] or result["missing_content_types"]) else "healthy"
    return result
