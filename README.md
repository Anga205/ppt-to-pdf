# PPT/PPTX and Document to PDF API

A HTTP service that converts PowerPoint and Writer-style document files to PDF.

- `POST /convert/ppt` — PowerPoint (`.ppt`, `.pptx`, `.pdf` passthrough)
- `POST /convert/doc` — Documents (`.doc`, `.docx`, `.docm`, `.dot`, `.dotx`, `.dotm`, `.odt`, `.ott`, `.rtf`, `.txt`, `.html`/`.htm`)
- Aggressive recovery pipelines for both presentation and document formats
- Concurrent conversion limiting via `CONCURRENT_CONVERSIONS`

---

## Quick start

<details>
<summary><b>Install & run (click to expand)</b></summary>

```bash
# 1. Install Python dependencies
pip install -r requirements.txt

# 2. (Optional) copy the environment template
cp .env.example .env

# 3. Start the server
uvicorn main:app --host 0.0.0.0 --port 8000
```

The service is now available at `http://localhost:8000`.

- Interactive API docs: <http://localhost:8000/docs>
- ReDoc: <http://localhost:8000/redoc>

</details>

<details>
<summary><b>Run with Docker (click to expand)</b></summary>

```bash
docker build -t ppt-to-pdf .
docker run -p 8000:8000 ppt-to-pdf
```

</details>

---

## Supported file types by route

<details>
<summary><b>Click to expand</b></summary>

### `POST /convert/ppt`
| Extension | Description |
|-----------|-------------|
| `.ppt` | Legacy PowerPoint binary (OLE) |
| `.pptx` | Office Open XML presentation |
| `.pdf` | Passthrough — returned as-is, no conversion |

### `POST /convert/doc`
| Extension | Description |
|-----------|-------------|
| `.doc` | Legacy Word binary (OLE) |
| `.docx` | Office Open XML document |
| `.docm` | Macro-enabled document |
| `.dot` | Legacy Word template |
| `.dotx` | Word template |
| `.dotm` | Macro-enabled template |
| `.odt` | OpenDocument Text |
| `.ott` | OpenDocument template |
| `.rtf` | Rich Text Format |
| `.txt` | Plain text |
| `.html` / `.htm` | HTML document |

</details>

---

## What each route does

<details>
<summary><b>Click to expand</b></summary>

### `GET /`
Returns an HTML wrapper page that uploads files and calls the conversion endpoints. Links to `/docs`, `/redoc`, and the repository.

### `GET /docs`
Swagger UI documentation (FastAPI default).

### `GET /redoc`
ReDoc documentation.

### `POST /convert/ppt`
Accepts a multipart upload (`file` or `upload`), validates the extension against `.ppt`/`.pptx`/`.pdf`, writes the file to a temporary directory, runs the conversion off the event loop via `run_in_threadpool`, and returns `application/pdf` with `Content-Disposition: attachment; filename="...pdf"`. Uses the LibreOffice Impress filter (`pdf:impress_pdf_Export`) with isolated user profiles.

### `POST /convert/doc`
Same upload conventions, validates against `DOCUMENT_ALLOWED_EXTENSIONS`, uses the LibreOffice Writer filter (`pdf:writer_pdf_Export`) with isolated profiles. If direct conversion fails, runs the document recovery pipeline (validation → conservative repair → progressive isolation → part isolation → content reconstruction → legacy `.doc` OLE → last-resort reconstruction) before returning an error.

</details>

---

## How output is handled

<details>
<summary><b>Click to expand</b></summary>

- Both conversion routes return a `StreamingResponse` with `media_type="application/pdf"`.
- The output filename is derived from the original upload stem plus `.pdf` (e.g. `slides.pptx` → `slides.pdf`).
- Temporary directories are cleaned up automatically via `tempfile.TemporaryDirectory`.
- The generated PDF is validated with `file_has_content` and `pypdf` scoring where applicable.
- Concurrent conversions are limited by a `ConversionLimiter` (a `BoundedSemaphore`); the slot is always released, even on failure.

</details>

---

## Error handling

<details>
<summary><b>Click to expand</b></summary>

| Status | When | Example `detail` |
|--------|------|------------------|
| `400` | Missing upload field | `"Missing upload. Use multipart form field named file."` |
| `400` | Unsupported extension on `/convert/ppt` | `"Only .ppt, .pptx, and .pdf files are supported"` |
| `400` | Unsupported extension on `/convert/doc` | `"Unsupported document format"` |
| `500` | Conversion failed after all recovery attempts | `"Conversion failed"` / `"Document conversion failed"` |

</details>

---

## Sample code

### PPT route

<details>
<summary><b>Click to expand</b></summary>

**curl**

```bash
curl -X POST "https://ppt2pdf.anga.codes/convert/ppt" \
  -F "file=@./slides.pptx" \
  --output slides.pdf
```

**Python**

```python
import requests

with open("slides.pptx", "rb") as f:
    r = requests.post("http://localhost:8000/convert/ppt", files={"file": f})
open("slides.pdf", "wb").write(r.content)
```

</details>

### Document route

<details>
<summary><b>Click to expand</b></summary>

**curl**

```bash
curl -X POST "https://ppt2pdf.anga.codes/convert/doc" \
  -F "file=@./document.docx" \
  --output document.pdf
```

**Python**

```python
import requests

with open("document.docx", "rb") as f:
    r = requests.post("http://localhost:8000/convert/doc", files={"file": f})
open("document.pdf", "wb").write(r.content)
```

</details>

---

## Broken file recovery

<details>
<summary><b>Click to expand</b></summary>

When conversion fails, the service does not fail immediately.

**PPT recovery stages:**
1. Direct LibreOffice conversion with several internal strategies
2. PPTX repair: clean re-zip (junk entry removal and normalization)
3. PPTX repair: flatten single nested root folder
4. PPTX repair: store-only re-pack
5. Legacy OLE (`.ppt`) retry path
6. Extension-variant retries (`.pptx` and `.ppt` copies)

**Document recovery stages:**
1. Direct LibreOffice Writer conversion
2. Structural diagnosis (ZIP/OOXML validation, CRC errors, missing `word/document.xml`)
3. Conservative OOXML repair (XML fix, dangling relationship removal, content-type repair)
4. Progressive isolation (embedded objects, media, macros removed)
5. Part isolation (headers/footers/footnotes/endnotes/comments tested individually)
6. Content reconstruction (text extraction + `weasyprint`/`reportlab` PDF rebuild)
7. Legacy `.doc` OLE inspection and conversion
8. Last-resort reconstruction

If all attempts fail, the API returns `500` with `"Conversion failed"`.

</details>

---

## Environment / configuration

<details>
<summary><b>Click to expand</b></summary>

Copy `.env.example` to `.env` and adjust:

- `CONCURRENT_CONVERSIONS` — max simultaneous conversions (default `1`)
- `RECOVERY_TEMP_DIR` — base directory for recovery temp files (default `/tmp`)

Swagger docs: `/docs`  
Redoc: `/redoc`

</details>

---

## File structure

<details>
<summary><b>Click to expand</b></summary>

```
app/
├── api.py                      # FastAPI routes (/convert/ppt, /convert/doc)
├── concurrency.py              # ConversionLimiter + CONCURRENT_CONVERSIONS
├── constants.py                # Allowed extensions, LibreOffice flags
├── logging_config.py           # Logging setup
├── recovery/                   # Broken-file recovery pipelines
│   ├── document_*.py           # Document recovery stages
│   ├── engines.py              # LibreOffice engine wrappers
│   ├── fonts.py                # Font handling
│   ├── last_resort.py          # Last-resort PDF reconstruction
│   ├── minimal_repair.py       # Minimal PPTX repair
│   ├── pipeline.py             # PPT recovery pipeline
│   ├── pptx_repair.py          # PPTX re-zip / flatten / store-only repair
│   ├── report.py               # Recovery report
│   ├── scoring.py              # PDF scoring
│   ├── slide_*.py              # Slide isolation / reconstruction
│   └── validator.py            # ZIP/OOXML diagnosis
├── services/
│   ├── conversion_service.py   # PPT conversion (with limiter)
│   ├── document_service.py     # Document conversion
│   ├── libreoffice_converter.py
│   ├── powerpoint_com.py       # Windows PowerPoint COM path
│   ├── repair_utils.py
│   └── unoconv_converter.py
└── utils/
    ├── command_runner.py
    └── file_ops.py
```

</details>

---

## Running tests / CI

<details>
<summary><b>Click to expand</b></summary>

```bash
# Unit tests (no LibreOffice required for most)
python -m pytest tests/ -v

# Integration tests against a running service
python tests/integration_test.py
```

The GitHub Actions workflow (`test` job) installs LibreOffice, generates fixtures, and runs the full suite. The `integration` job starts the service and runs `tests/integration_test.py` at concurrency limits `1` and `3`.

</details>
