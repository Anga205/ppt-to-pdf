"""Comprehensive multi-stage recovery pipeline."""
import logging
import shutil
from pathlib import Path

from app.recovery.report import RecoveryReport
from app.recovery.validator import diagnose_pptx_structure
from app.recovery.minimal_repair import repair_oooxml_minimal
from app.recovery.pptx_repair import try_python_pptx_repair
from app.recovery.legacy_ole import inspect_ole_streams
from app.recovery.engines import try_engine
from app.recovery.fonts import detect_missing_fonts
from app.recovery.last_resort import reconstruct_pdf_from_content
from app.recovery.logging_diag import safe_temp_dir


def run_full_recovery(input_path: Path, pdf_path: Path) -> RecoveryReport:
    report = RecoveryReport(original_path=input_path, original_type="pptx" if input_path.suffix == ".pptx" else "ppt")
    work_dir = safe_temp_dir()
    try:
        # Stage 1: Direct conversion (existing) - import locally to avoid circular
        from app.services.conversion_service import convert_with_libreoffice
        report.attempted_strategies.append("direct_libreoffice")
        try:
            if convert_with_libreoffice(input_path, pdf_path):
                report.successful_strategy = "direct_libreoffice"
                report.engine_used = "libreoffice"
                report.final_pdf_path = pdf_path
                report.final_pdf_size = pdf_path.stat().st_size
                return report
        except Exception as exc:
            report.errors.append(f"Direct conversion failed: {exc}")

        # Stage 2: Validation / diagnosis
        report.attempted_strategies.append("structural_diagnosis")
        diag = diagnose_pptx_structure(input_path)
        report.detected_corruption = diag.get("crc_errors", []) + diag.get("dangling_rels", []) + (["missing_presentation_xml"] if diag.get("missing_presentation_xml") else [])
        if diag.get("overall_health") == "corrupt":
            report.warnings.append("Structural diagnosis indicates corruption")

        # Stage 3: Minimal OOXML repair
        report.attempted_strategies.append("minimal_oooxml_repair")
        repaired_path = work_dir / "repaired_minimal.pptx"
        if repair_oooxml_minimal(input_path, repaired_path):
            report.repaired_components.append("oooxml_xml")
            report.attempted_strategies.append("libreoffice_after_minimal_repair")
            try:
                from app.services.conversion_service import convert_with_libreoffice
                if convert_with_libreoffice(repaired_path, pdf_path):
                    report.successful_strategy = "minimal_oooxml_repair"
                    report.engine_used = "libreoffice"
                    report.final_pdf_path = pdf_path
                    report.final_pdf_size = pdf_path.stat().st_size
                    return report
            except Exception as exc:
                report.errors.append(f"Conversion after minimal repair failed: {exc}")

        # Stage 4: python-pptx recovery
        report.attempted_strategies.append("python_pptx_repair")
        pptx_repaired = work_dir / "repaired_pptx.pptx"
        if try_python_pptx_repair(input_path, pptx_repaired):
            report.repaired_components.append("python_pptx_resave")
            try:
                from app.services.conversion_service import convert_with_libreoffice
                if convert_with_libreoffice(pptx_repaired, pdf_path):
                    report.successful_strategy = "python_pptx_repair"
                    report.engine_used = "libreoffice"
                    report.final_pdf_path = pdf_path
                    report.final_pdf_size = pdf_path.stat().st_size
                    return report
            except Exception as exc:
                report.errors.append(f"Conversion after python-pptx repair failed: {exc}")

        # Stage 8: Legacy OLE deep repair
        if input_path.suffix.lower() == ".ppt":
            report.attempted_strategies.append("ole_inspection")
            ole_info = inspect_ole_streams(input_path)
            if ole_info.get("has_powerpoint_document"):
                report.repaired_components.append("ole_stream_inspected")

        # Stage 9: Engine selection (try all independent)
        for engine in ["libreoffice_generic", "unoconv", "powerpoint_com"]:
            report.attempted_strategies.append(f"engine_{engine}")
            try:
                if try_engine(engine, input_path, pdf_path):
                    report.successful_strategy = f"engine_{engine}"
                    report.engine_used = engine
                    report.final_pdf_path = pdf_path
                    report.final_pdf_size = pdf_path.stat().st_size
                    return report
            except Exception as exc:
                report.errors.append(f"Engine {engine} crashed: {exc}")

        # Stage 10: Font substitution (recorded, not fully implemented)
        report.attempted_strategies.append("font_substitution")
        missing_fonts = detect_missing_fonts(input_path)
        if missing_fonts:
            report.font_substitutions = missing_fonts

        # Stage 11: Last-resort reconstruction
        report.attempted_strategies.append("last_resort_reconstruction")
        if reconstruct_pdf_from_content(input_path, pdf_path):
            report.successful_strategy = "last_resort_reconstruction"
            report.engine_used = "reconstructed"
            report.reconstructed = True
            report.final_pdf_path = pdf_path
            report.final_pdf_size = pdf_path.stat().st_size
            return report

        # Nothing worked
        report.errors.append("All recovery stages failed")
        return report
    finally:
        # Cleanup work dir (keep only if needed for debugging)
        try:
            shutil.rmtree(str(work_dir), ignore_errors=True)
        except Exception:
            pass
