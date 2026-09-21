import logging
import tempfile
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, File, HTTPException, UploadFile

from fastapi.responses import StreamingResponse
from starlette.concurrency import run_in_threadpool

from app.constants import ALLOWED_EXTENSIONS, DOCUMENT_ALLOWED_EXTENSIONS
from app.logging_config import configure_logging
from app.services.conversion_service import convert_file
from app.services.document_service import convert_document_file
from app.utils.file_ops import copy_stream_to_path, file_has_content, read_file_bytes


configure_logging()

app = FastAPI(title="PPT/PPTX to PDF Converter")

def _validate_extension(filename):
    extension = Path(filename).suffix.lower()
    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Only .ppt, .pptx, and .pdf files are supported")
    return extension


def _validate_document_extension(filename):
    extension = Path(filename).suffix.lower()
    if extension not in DOCUMENT_ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Unsupported document format")
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


async def _convert_upload_to_pdf_bytes(upload_stream, extension):
    with tempfile.TemporaryDirectory() as temp_dir_name:
        temp_dir = Path(temp_dir_name)
        input_path = temp_dir / f"input{extension}"
        output_path = temp_dir / "output.pdf"
        copy_stream_to_path(upload_stream, input_path)
        if extension == ".pdf":
            return read_file_bytes(input_path)
        # Run the blocking conversion off the event loop so the concurrency
        # limiter can actually allow parallel conversions.
        await run_in_threadpool(convert_file, input_path, output_path)
        if not file_has_content(output_path):
            raise RuntimeError("Conversion failed")
        return read_file_bytes(output_path)


async def _convert_document_upload_to_pdf_bytes(upload_stream, extension):
    with tempfile.TemporaryDirectory() as temp_dir_name:
        temp_dir = Path(temp_dir_name)
        input_path = temp_dir / f"input{extension}"
        output_path = temp_dir / "output.pdf"
        copy_stream_to_path(upload_stream, input_path)
        await run_in_threadpool(convert_document_file, input_path, output_path)
        if not file_has_content(output_path):
            raise RuntimeError("Document conversion failed")
        return read_file_bytes(output_path)


@app.post("/convert/ppt")
async def convert_ppt_endpoint(
    file: Optional[UploadFile] = File(default=None),
    upload: Optional[UploadFile] = File(default=None),
):
    selected_file = _pick_upload(file, upload)
    original_name = selected_file.filename or "upload.pptx"
    try:
        extension = _validate_extension(original_name)
        pdf_bytes = await _convert_upload_to_pdf_bytes(selected_file.file, extension)
    except HTTPException:
        raise
    except Exception as exc:
        logging.error("Unhandled conversion error: %s", exc)
        raise HTTPException(status_code=500, detail="Conversion failed") from exc
    finally:
        await selected_file.close()

    headers = _build_response_headers(original_name)
    return StreamingResponse(iter([pdf_bytes]), media_type="application/pdf", headers=headers)


@app.post("/convert/doc")
async def convert_doc_endpoint(
    file: Optional[UploadFile] = File(default=None),
    upload: Optional[UploadFile] = File(default=None),
):
    selected_file = _pick_upload(file, upload)
    original_name = selected_file.filename or "upload.docx"
    try:
        extension = _validate_document_extension(original_name)
        pdf_bytes = await _convert_document_upload_to_pdf_bytes(selected_file.file, extension)
    except HTTPException:
        raise
    except Exception as exc:
        logging.error("Unhandled document conversion error: %s", exc)
        raise HTTPException(status_code=500, detail="Document conversion failed") from exc
    finally:
        await selected_file.close()
    headers = _build_response_headers(original_name)
    return StreamingResponse(iter([pdf_bytes]), media_type="application/pdf", headers=headers)
