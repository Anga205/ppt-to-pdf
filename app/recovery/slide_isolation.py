"""Stage 6: Slide isolation — binary-search / divide-and-conquer recovery."""
import logging
import zipfile
import tempfile
import shutil
from pathlib import Path

from app.services.conversion_service import convert_file


def isolate_and_convert_slides(input_path: Path, pdf_path: Path, work_dir: Path) -> bool:
    """Try to recover presentation by isolating slides and converting individually."""
    try:
        with tempfile.TemporaryDirectory() as td:
            extract_dir = Path(td) / "extracted"
            extract_dir.mkdir()
            with zipfile.ZipFile(str(input_path), "r") as zf:
                zf.extractall(str(extract_dir))
            slide_files = sorted([p for p in extract_dir.rglob("ppt/slides/slide*.xml") if p.is_file() and not p.name.startswith("_rels")])
            if not slide_files:
                return False
            # Build minimal PPTX per slide (simplified: copy full package, remove other slides)
            slide_pdfs = []
            for idx, slide_file in enumerate(slide_files):
                slide_dir = work_dir / f"slide_{idx}"
                slide_dir.mkdir(parents=True, exist_ok=True)
                # Copy full package and delete other slides
                with zipfile.ZipFile(str(input_path), "r") as zin:
                    with zipfile.ZipFile(str(slide_dir / "in.pptx"), "w", zipfile.ZIP_DEFLATED) as zout:
                        for item in zin.infolist():
                            if item.filename.startswith("ppt/slides/slide") and item.filename.endswith(".xml"):
                                # Only keep this slide
                                if item.filename == slide_file.relative_to(extract_dir).as_posix():
                                    zout.writestr(item.filename, zin.read(item.filename))
                            else:
                                zout.writestr(item.filename, zin.read(item.filename))
                out_pdf = slide_dir / "out.pdf"
                try:
                    convert_file(slide_dir / "in.pptx", out_pdf)
                    if out_pdf.exists() and out_pdf.stat().st_size > 0:
                        slide_pdfs.append(out_pdf)
                except Exception:
                    pass
            if not slide_pdfs:
                return False
            # Merge PDFs in original order
            try:
                from pypdf import PdfWriter, PdfReader
                writer = PdfWriter()
                for p in slide_pdfs:
                    writer.append(str(p))
                writer.write(str(pdf_path))
                return pdf_path.exists() and pdf_path.stat().st_size > 0
            except Exception:
                # Fallback: just copy first successful slide PDF
                shutil.copy2(str(slide_pdfs[0]), str(pdf_path))
                return pdf_path.exists() and pdf_path.stat().st_size > 0
    except Exception as exc:
        logging.error("Slide isolation failed: %s", exc)
        return False
