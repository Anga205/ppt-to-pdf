"""Comprehensive multi-stage document recovery pipeline."""
import logging
from pathlib import Path
from app.recovery.report import RecoveryReport
from app.recovery.document_validator import diagnose_document_structure
from app.recovery.document_repair import repair_document_oooxml
from app.recovery.document_isolation import progressive_document_isolation
from app.recovery.document_reconstruct import reconstruct_document_pdf
from app.recovery.document_legacy_ole import inspect_document_ole
from app.recovery.logging_diag import safe_temp_dir


def run_document_recovery(input_path: Path, pdf_path: Path) -> RecoveryReport:
    report = RecoveryReport(
        original_path=input_path,
        original_type="docx" if input_path.suffix == ".docx" else ("doc" if input_path.suffix == ".doc" else "document"),
    )
    work_dir = safe_temp_dir(prefix="doc-recovery-")
    try:
        from app.services.libreoffice_converter import convert_with_libreoffice_writer
        # Stage 1: Direct conversion
        report.attempted_strategies.append("direct_libreoffice_writer")
        try:
            if convert_with_libreoffice_writer(input_path, pdf_path):
                report.successful_strategy = "direct_libreoffice_writer"
                report.engine_used = "libreoffice_writer"
                report.final_pdf_path = pdf_path
                report.final_pdf_size = pdf_path.stat().st_size
                return report
        except Exception as exc:
            report.errors.append(f"Direct conversion failed: {exc}")

        # Stage 2: Structural diagnosis
        report.attempted_strategies.append("structural_diagnosis")
        diag = diagnose_document_structure(input_path)
        report.detected_corruption = diag.get("crc_errors", []) + ("missing_document_xml" if diag.get("missing_document_xml") else [])
        if diag.get("overall_health") == "corrupt":
            report.warnings.append("Structural diagnosis indicates corruption")

        # Stage 3: Conservative OOXML repair
        report.attempted_strategies.append("conservative_oooxml_repair")
        repaired_path = work_dir / "repaired_doc.docx"
        if repair_document_oooxml(input_path, repaired_path):
            report.repaired_components.append("oooxml_xml")
            try:
                if convert_document_file(repaired_path, pdf_path):
                    report.successful_strategy = "conservative_oooxml_repair"
                    report.engine_used = "libreoffice_writer"
                    report.final_pdf_path = pdf_path
                    report.final_pdf_size = pdf_path.stat().st_size
                    return report
            except Exception as exc:
                report.errors.append(f"Conversion after repair failed: {exc}")

        # Stage 4: Progressive isolation
        report.attempted_strategies.append("progressive_isolation")
        isolated_path = work_dir / "isolated.docx"
        if progressive_document_isolation(input_path, isolated_path):
            report.repaired_components.append("embedded_objects_removed")
            try:
                if convert_document_file(isolated_path, pdf_path):
                    report.successful_strategy = "progressive_isolation"
                    report.engine_used = "libreoffice_writer"
                    report.final_pdf_path = pdf_path
                    report.final_pdf_size = pdf_path.stat().st_size
                    return report
            except Exception as exc:
                report.errors.append(f"Conversion after isolation failed: {exc}")

        # Stage 5: Legacy .doc OLE
        report.attempted_strategies.append("legacy_ole_inspection")
        ole_info = inspect_document_ole(input_path)
        if ole_info.get("has_word_document"):
            report.attempted_strategies.append("legacy_ole_conversion")
            try:
                if convert_with_libreoffice_writer(input_path, pdf_path):
                    report.successful_strategy = "legacy_ole_conversion"
                    report.engine_used = "libreoffice_writer"
                    report.final_pdf_path = pdf_path
                    report.final_pdf_size = pdf_path.stat().st_size
                    return report
            except Exception as exc:
                report.errors.append(f"Legacy OLE conversion failed: {exc}")

        # Stage 6: Last-resort reconstruction
        report.attempted_strategies.append("last_resort_reconstruction")
        if reconstruct_document_pdf(input_path, pdf_path):
            report.successful_strategy = "last_resort_reconstruction"
            report.engine_used = "weasyprint"
            report.reconstructed = True
            report.final_pdf_path = pdf_path
            report.final_pdf_size = pdf_path.stat().st_size
            return report

        raise RuntimeError("Document conversion failed after all recovery stages")
    finally:
        # Cleanup handled by temporary directories; no persistent leaks
        pass
    return report
