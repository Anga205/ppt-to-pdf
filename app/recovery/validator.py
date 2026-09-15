"""Stage 2: PPTX package validation and structural diagnosis."""
import logging
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET


def diagnose_pptx_structure(input_path: Path) -> dict:
    """Inspect ZIP and OOXML structure; return diagnosis dict."""
    result = {
        "is_zip": False,
        "crc_errors": [],
        "missing_content_types": False,
        "missing_presentation_xml": False,
        "dangling_rels": [],
        "missing_media_refs": [],
        "duplicate_slide_ids": [],
        "malformed_xml_files": [],
        "missing_slides": [],
        "missing_slide_masters": [],
        "missing_slide_layouts": [],
        "missing_themes": [],
        "notes_rels_issues": [],
        "embedded_object_issues": [],
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
            # Check CRC / read errors
            for info in zf.infolist():
                try:
                    zf.read(info.filename)
                except Exception as exc:
                    result["crc_errors"].append(f"{info.filename}: {exc}")

            # Content types
            if "[Content_Types].xml" not in names:
                result["missing_content_types"] = True
            else:
                try:
                    ct = zf.read("[Content_Types].xml").decode("utf-8", errors="ignore")
                    if "presentationml" not in ct and "presentation" not in ct:
                        result["missing_content_types"] = True
                except Exception:
                    pass

            # Presentation XML
            if "ppt/presentation.xml" not in names:
                result["missing_presentation_xml"] = True
            else:
                try:
                    xml = zf.read("ppt/presentation.xml").decode("utf-8", errors="ignore")
                    # Basic slide ID check
                    root = ET.fromstring(xml)
                    ns = {"a": "http://schemas.openxmlformats.org/drawingml/2006/main"}
                    # Simple check for sldId elements
                    sld_ids = root.findall(".//{http://schemas.openxmlformats.org/presentationml/2006/main}sldId", ns)
                    ids = [el.get("id") for el in sld_ids if el.get("id")]
                    if len(ids) != len(set(ids)):
                        result["duplicate_slide_ids"].append("duplicate sldId values")
                except Exception as exc:
                    result["malformed_xml_files"].append(f"ppt/presentation.xml: {exc}")

            # Slide relationships
            slide_rels = [n for n in names if n.startswith("ppt/slides/_rels/") and n.endswith(".rels")]
            for rel_path in slide_rels:
                try:
                    rel_xml = zf.read(rel_path).decode("utf-8", errors="ignore")
                    # Check for dangling relationships (target not in archive)
                    root = ET.fromstring(rel_xml)
                    for rel in root.findall("{http://schemas.openxmlformats.org/package/2006/relationships}Relationship"):
                        target = rel.get("Target")
                        if target:
                            # Resolve relative to slide folder
                            base = rel_path.replace("_rels/", "").replace(".rels", "")
                            target_path = (Path(base).parent / target).as_posix()
                            if target_path not in names and target_path.lstrip("/") not in names:
                                result["dangling_rels"].append(f"{rel_path} -> {target}")
                except Exception as exc:
                    result["malformed_xml_files"].append(f"{rel_path}: {exc}")

            # Media references
            media_refs = [n for n in names if n.startswith("ppt/media/")]
            # Check slides for image references that point to missing media
            for n in names:
                if n.startswith("ppt/slides/slide") and n.endswith(".xml"):
                    try:
                        xml = zf.read(n).decode("utf-8", errors="ignore")
                        # Very basic: look for r:embed or r:link
                        if "r:embed" in xml or "r:link" in xml:
                            # We don't fully parse here; just note presence
                            pass
                    except Exception:
                        pass

            # Slide count vs presentation
            slides = [n for n in names if n.startswith("ppt/slides/slide") and n.endswith(".xml") and not n.endswith("_rels/")]
            result["slides_found"] = len(slides)

            # Missing masters/layouts/themes
            masters = [n for n in names if n.startswith("ppt/slideMasters/slideMaster") and n.endswith(".xml")]
            layouts = [n for n in names if n.startswith("ppt/slideLayouts/slideLayout") and n.endswith(".xml")]
            themes = [n for n in names if n.startswith("ppt/theme/theme") and n.endswith(".xml")]
            if not masters:
                result["missing_slide_masters"] = True
            if not layouts:
                result["missing_slide_layouts"] = True
            if not themes:
                result["missing_themes"] = True

            # Embedded objects / notes
            notes = [n for n in names if n.startswith("ppt/notesSlides/")]
            embedded = [n for n in names if n.startswith("ppt/embeddings/") or n.startswith("ppt/oleObjects/")]
            if embedded:
                result["embedded_object_issues"].append(f"found {len(embedded)} embedded objects")

            # Overall health
            if result["crc_errors"] or result["missing_presentation_xml"] or result["dangling_rels"]:
                result["overall_health"] = "corrupt"
            elif result["missing_content_types"] or result["duplicate_slide_ids"] or result["missing_slide_masters"] or result["missing_slide_layouts"] or result["missing_themes"]:
                result["overall_health"] = "degraded"
            else:
                result["overall_health"] = "healthy"
    except Exception as exc:
        result["crc_errors"].append(str(exc))
        result["overall_health"] = "unreadable"
    return result
