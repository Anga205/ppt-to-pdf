"""Stage 3: Conservative OOXML document repair."""
import logging
import zipfile
import tempfile
import shutil
from pathlib import Path
from xml.etree import ElementTree as ET


def _fix_xml_string(xml_str: str) -> str:
    return xml_str.replace("\x00", "")


def repair_document_oooxml(input_path: Path, repaired_path: Path) -> bool:
    try:
        with tempfile.TemporaryDirectory() as td:
            extract_dir = Path(td) / "extracted"
            extract_dir.mkdir()
            with zipfile.ZipFile(str(input_path), "r") as zf:
                zf.extractall(str(extract_dir))
            changed = False
            # Fix word/document.xml basic issues
            doc_path = extract_dir / "word" / "document.xml"
            if doc_path.exists():
                try:
                    xml = _fix_xml_string(doc_path.read_text(encoding="utf-8", errors="ignore"))
                    root = ET.fromstring(xml)
                    # Minimal repair: remove null bytes already done; preserve structure
                    doc_path.write_text(xml, encoding="utf-8")
                except Exception as exc:
                    logging.warning("Could not repair document.xml: %s", exc)
            # Drop dangling relationships in word/_rels/
            rels_dir = extract_dir / "word" / "_rels"
            if rels_dir.exists():
                for rel_file in rels_dir.glob("*.rels"):
                    try:
                        xml = _fix_xml_string(rel_file.read_text(encoding="utf-8", errors="ignore"))
                        root = ET.fromstring(xml)
                        # Remove relationships with missing targets (simplified)
                        rels = root.findall("{http://schemas.openxmlformats.org/package/2006/relationships}Relationship")
                        for rel in rels:
                            target = rel.get("Target")
                            if target and target.startswith("/"):
                                # Check if target exists relative to package
                                target_path = extract_dir / target.lstrip("/")
                                if not target_path.exists():
                                    root.remove(rel)
                                    changed = True
                        rel_file.write_text(ET.tostring(root, encoding="unicode"), encoding="utf-8")
                        if changed:
                            pass  # already tracked
                    except Exception as exc:
                        logging.warning("Could not repair rels %s: %s", rel_file, exc)
            # Repair content types if missing
            ct_path = extract_dir / "[Content_Types].xml"
            if ct_path.exists():
                try:
                    xml = _fix_xml_string(ct_path.read_text(encoding="utf-8", errors="ignore"))
                    root = ET.fromstring(xml)
                    # Ensure wordprocessingml content type present
                    ns = {"ct": "http://schemas.openxmlformats.org/package/2006/content-types"}
                    defaults = root.findall("ct:Default", ns)
                    has_word = any("wordprocessingml" in (d.get("Extension") or "") for d in defaults)
                    if not has_word:
                        # Add default for xml
                        new_default = ET.SubElement(root, "{http://schemas.openxmlformats.org/package/2006/content-types}Default")
                        new_default.set("Extension", "xml")
                        new_default.set("ContentType", "application/xml")
                        changed = True
                    ct_path.write_text(ET.tostring(root, encoding="unicode"), encoding="utf-8")
                except Exception as exc:
                    logging.warning("Could not repair content types: %s", exc)
            # Repackage
            repaired_path.parent.mkdir(parents=True, exist_ok=True)
            with zipfile.ZipFile(str(repaired_path), "w", compression=zipfile.ZIP_DEFLATED) as zf:
                for file_path in extract_dir.rglob("*"):
                    if file_path.is_file():
                        zf.write(str(file_path), file_path.relative_to(extract_dir).as_posix())
            return repaired_path.exists() and repaired_path.stat().st_size > 0
    except Exception as exc:
        logging.error("Document repair failed: %s", exc)
        return False
