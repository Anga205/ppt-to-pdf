"""Stage 3: Minimal conservative OOXML repair."""
import logging
import zipfile
import tempfile
from pathlib import Path
from xml.etree import ElementTree as ET


def _fix_xml_string(xml_str: str) -> str:
    # Minimal: remove null bytes, fix common encoding issues
    return xml_str.replace("\x00", "")


def repair_oooxml_minimal(input_path: Path, repaired_path: Path) -> bool:
    """Conservative repair: fix XML, drop dangling rels, fix content types.

    Only rewrites a part when an actual change is made, so healthy XML is
    preserved byte-for-byte.
    """
    try:
        with tempfile.TemporaryDirectory() as td:
            extract_dir = Path(td) / "extracted"
            extract_dir.mkdir()
            with zipfile.ZipFile(str(input_path), "r") as zf:
                zf.extractall(str(extract_dir))

            changed = False

            # Fix presentation.xml slide IDs if duplicates
            pres_path = extract_dir / "ppt" / "presentation.xml"
            if pres_path.exists():
                try:
                    xml = _fix_xml_string(pres_path.read_text(encoding="utf-8", errors="ignore"))
                    root = ET.fromstring(xml)
                    ns = {"p": "http://schemas.openxmlformats.org/presentationml/2006/main"}
                    sld_ids = root.findall(".//p:sldId", ns)
                    seen = set()
                    local_changed = False
                    for el in sld_ids:
                        sid = el.get("id")
                        if sid in seen:
                            try:
                                new_id = str(int(sid) + 10000)
                                el.set("id", new_id)
                                local_changed = True
                            except Exception:
                                pass
                        seen.add(el.get("id"))
                    if local_changed:
                        pres_path.write_text(ET.tostring(root, encoding="unicode"), encoding="utf-8")
                        changed = True
                except Exception as exc:
                    logging.warning("Could not repair presentation.xml: %s", exc)

            # Drop dangling relationships in slide rels
            rels_dir = extract_dir / "ppt" / "slides" / "_rels"
            if rels_dir.exists():
                for rel_file in rels_dir.glob("*.rels"):
                    try:
                        xml = _fix_xml_string(rel_file.read_text(encoding="utf-8", errors="ignore"))
                        root = ET.fromstring(xml)
                        ns = {"r": "http://schemas.openxmlformats.org/package/2006/relationships"}
                        to_remove = []
                        for rel in root.findall("r:Relationship", ns):
                            target = rel.get("Target")
                            if target:
                                # Resolve relative to slide folder
                                slide_folder = rel_file.parent.parent
                                target_path = (slide_folder / target).resolve()
                                if not target_path.exists():
                                    to_remove.append(rel)
                        if to_remove:
                            for rel in to_remove:
                                root.remove(rel)
                            rel_file.write_text(ET.tostring(root, encoding="unicode"), encoding="utf-8")
                            changed = True
                    except Exception as exc:
                        logging.warning("Could not repair %s: %s", rel_file, exc)

            # Rebuild [Content_Types].xml if missing or broken
            ct_path = extract_dir / "[Content_Types].xml"
            if not ct_path.exists() or ct_path.stat().st_size < 100:
                ct_content = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
<Default Extension="xml" ContentType="application/xml"/>
<Override PartName="/ppt/presentation.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.presentation.main+xml"/>
</Types>'''
                ct_path.write_text(ct_content, encoding="utf-8")
                changed = True

            # Repack
            repaired_path.parent.mkdir(parents=True, exist_ok=True)
            with zipfile.ZipFile(str(repaired_path), "w", compression=zipfile.ZIP_DEFLATED) as zf:
                for file_path in extract_dir.rglob("*"):
                    if file_path.is_file():
                        arcname = file_path.relative_to(extract_dir).as_posix()
                        zf.write(str(file_path), arcname)
            return repaired_path.exists() and repaired_path.stat().st_size > 0
    except Exception as exc:
        logging.error("Minimal OOXML repair failed: %s", exc)
        return False
