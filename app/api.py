import logging
import tempfile
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse, StreamingResponse

from app.constants import ALLOWED_EXTENSIONS
from app.logging_config import configure_logging
from app.services.conversion_service import convert_file
from app.utils.file_ops import copy_stream_to_path, file_has_content, read_file_bytes


configure_logging()
app = FastAPI(title="PPT/PPTX to PDF Converter")


def _frontend_path():
    return Path(__file__).resolve().parent / "static" / "index.html"


def _validate_extension(filename):
    extension = Path(filename).suffix.lower()
    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Only .ppt, .pptx, and .pdf files are supported")
    return extension


def _pick_upload(file_obj, upload_obj):
    selected = file_obj or upload_obj
    if selected is None:
        raise HTTPException(
            status_code=400,
            detail="Missing upload. Use multipart form field named file.",
        )
    return selected


def _build_response_headers(original_name):
    output_name = f"{Path(original_name).stem}.pdf"
    return {"Content-Disposition": f'attachment; filename="{output_name}"'}


def _convert_upload_to_pdf_bytes(upload_stream, extension):
    with tempfile.TemporaryDirectory() as temp_dir_name:
        temp_dir = Path(temp_dir_name)
        input_path = temp_dir / f"input{extension}"
        output_path = temp_dir / "output.pdf"
        copy_stream_to_path(upload_stream, input_path)
        if extension == ".pdf":
            return read_file_bytes(input_path)
        convert_file(input_path, output_path)
        if not file_has_content(output_path):
            raise RuntimeError("Conversion failed")
        return read_file_bytes(output_path)


@app.get("/")
def root():
    return FileResponse(_frontend_path(), media_type="text/html")


@app.post("/convert")
async def convert_endpoint(
    file: Optional[UploadFile] = File(default=None),
    upload: Optional[UploadFile] = File(default=None),
):
    selected_file = _pick_upload(file, upload)
    original_name = selected_file.filename or "upload.pptx"
    try:
        extension = _validate_extension(original_name)
        pdf_bytes = _convert_upload_to_pdf_bytes(selected_file.file, extension)
    except HTTPException:
        raise
    except Exception as exc:
        logging.error("Unhandled conversion error: %s", exc)
        raise HTTPException(status_code=500, detail="Conversion failed") from exc
    finally:
        await selected_file.close()

    headers = _build_response_headers(original_name)
    return StreamingResponse(iter([pdf_bytes]), media_type="application/pdf", headers=headers)
