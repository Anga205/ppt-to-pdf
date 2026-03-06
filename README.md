# PPT/PPTX to PDF API

This is a simple HTTP api that takes a pptx or ppt file and returns a file in PDF format

This api will still work with broken pptx files, including ones compiled in really old versions of powerpoint (like the broken pptx files on [pesuacademy](https://pesuacademy.com))

## What the API Does

- Accepts a single uploaded presentation file using `multipart/form-data`.
- Supports input extensions: `.ppt`, `.pptx`.
- Produces a PDF file as the response stream.
- Uses multiple conversion engines in a strict fallback order.

## Conversion Flow (Exact Order)

The service follows this exact sequence:

1. Windows PowerPoint COM (Windows only)
2. unoconv
3. LibreOffice strategies in order:
   - Strategy 3.1: `--convert-to pdf:impress_pdf_Export`
   - Strategy 3.2: `--convert-to pdf`
   - Strategy 3.3: short-path retry using `temp/in.pptx` or `temp/in.ppt`
   - Strategy 3.4: two-step conversion (`ppt/pptx -> odp -> pdf`)
4. PPTX ZIP repair and then retry LibreOffice
5. Legacy container detection (OLE) and retry with `temp/in.ppt`
6. Failure response: HTTP 500 with `"Conversion failed"`

## Project Structure

- `main.py`: local runtime launcher (`python3 main.py`) using uvicorn
- `app/api.py`: FastAPI app and request/response handling
- `app/services/`: conversion strategies and orchestration
- `app/utils/`: shared command and file utilities
- `fastapi_app.py`: compatibility export of the `app` object

## Requirements

- Python 3.10+
- FastAPI + uvicorn
- `python-multipart` for file upload parsing
- Optional platform tools:
  - Windows: Microsoft PowerPoint + `pywin32`
  - Linux/macOS: LibreOffice (`soffice`/`libreoffice`) and optionally `unoconv`

Install dependencies:

```bash
pip install -r requirements.txt
```

## Run the API

```bash
python3 main.py
```

Default bind address is `0.0.0.0:8000`.

## Endpoint

- Method: `POST`
- Path: `/convert`
- Content type: `multipart/form-data`
- Form field name: `file`
- Input file types: `.ppt`, `.pptx`
- Success response: `application/pdf`

## Sample cURL Commands

<details>
<summary>click to view sample curl command</summary>

```bash
curl -X POST "http://127.0.0.1:8000/convert" \
  -F "file=@./slides.pptx" \
  --output slides.pdf
```

</details>

<details>
<summary>click to view sample curl command</summary>

```bash
curl -X POST "http://127.0.0.1:8000/convert" \
  -F "file=@./legacy.ppt" \
  --output legacy.pdf
```

</details>

## Error Responses

- `400` if the uploaded extension is not `.ppt` or `.pptx`
- `500` if all conversion strategies fail, response detail is `"Conversion failed"`

## Notes for Production Use

- Ensure LibreOffice is installed and available in `PATH` on non-Windows hosts.
- Run behind a reverse proxy (Nginx, Traefik, or cloud gateway) for TLS and request limits.
- Consider process isolation or queue-based execution for large batch workloads.
- Keep logs enabled for strategy-level observability and troubleshooting.
