"""Generate sample PPTX fixtures for tests.

Run:  python tests/fixtures/generate_fixtures.py
Produces healthy and corrupted PPTX files under tests/fixtures/.
"""
import shutil
import sys
import zipfile
from pathlib import Path

from pptx import Presentation
from pptx.util import Inches, Pt

FIXTURE_DIR = Path(__file__).resolve().parent


def _make_healthy_pptx(path: Path, slides: int = 3):
    prs = Presentation()
    for i in range(slides):
        slide = prs.slides.add_slide(prs.slide_layouts[1])
        title = slide.shapes.title
        title.text = f"Slide {i + 1}"
        body = slide.placeholders[1]
        body.text = f"Content for slide {i + 1}\nLine two"
    prs.save(str(path))


def _make_corrupt_missing_media(path: Path):
    """Healthy PPTX with a dangling image relationship (missing media part)."""
    prs = Presentation()
    slide = prs.slides.add_slide(prs.slide_layouts[1])
    slide.shapes.title.text = "Missing media slide"
    tmp = path.with_suffix(".tmp.pptx")
    prs.save(str(tmp))
    # Rezip, dropping ppt/media/* but keeping the relationship that references it.
    with zipfile.ZipFile(str(tmp), "r") as zin:
        names = zin.namelist()
        with zipfile.ZipFile(str(path), "w", zipfile.ZIP_DEFLATED) as zout:
            for name in names:
                if name.startswith("ppt/media/"):
                    continue
                zout.writestr(name, zin.read(name))
    tmp.unlink()


def _make_corrupt_malformed_xml(path: Path):
    """Healthy PPTX with a malformed slide XML (truncated)."""
    prs = Presentation()
    slide = prs.slides.add_slide(prs.slide_layouts[1])
    slide.shapes.title.text = "Malformed XML slide"
    tmp = path.with_suffix(".tmp.pptx")
    prs.save(str(tmp))
    with zipfile.ZipFile(str(tmp), "r") as zin:
        names = zin.namelist()
        with zipfile.ZipFile(str(path), "w", zipfile.ZIP_DEFLATED) as zout:
            for name in names:
                data = zin.read(name)
                if name.startswith("ppt/slides/slide") and name.endswith(".xml"):
                    # Truncate the XML to make it malformed.
                    data = data[: len(data) // 2]
                zout.writestr(name, data)
    tmp.unlink()


def _make_corrupt_missing_slide(path: Path):
    """Healthy PPTX with a slide removed but still referenced in presentation.xml."""
    prs = Presentation()
    for i in range(3):
        slide = prs.slides.add_slide(prs.slide_layouts[1])
        slide.shapes.title.text = f"Slide {i + 1}"
    tmp = path.with_suffix(".tmp.pptx")
    prs.save(str(tmp))
    with zipfile.ZipFile(str(tmp), "r") as zin:
        names = zin.namelist()
        with zipfile.ZipFile(str(path), "w", zipfile.ZIP_DEFLATED) as zout:
            for name in names:
                if name.startswith("ppt/slides/slide2"):
                    continue
                zout.writestr(name, zin.read(name))
    tmp.unlink()


def main():
    FIXTURE_DIR.mkdir(parents=True, exist_ok=True)
    _make_healthy_pptx(FIXTURE_DIR / "sample.pptx", slides=3)
    _make_corrupt_missing_media(FIXTURE_DIR / "corrupt_missing_media.pptx")
    _make_corrupt_malformed_xml(FIXTURE_DIR / "corrupt_malformed_xml.pptx")
    _make_corrupt_missing_slide(FIXTURE_DIR / "corrupt_missing_slide.pptx")
    print(f"Fixtures written to {FIXTURE_DIR}")


if __name__ == "__main__":
    main()