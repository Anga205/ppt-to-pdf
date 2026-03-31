# PPT/PPTX to PDF API

Simple FastAPI service that converts PowerPoint files to PDF.

The API is designed for caller simplicity:

- One main endpoint: `POST /convert`
- Upload one file and receive one PDF
- No platform-specific API behavior
- Built-in retry and repair flow for damaged files

## Why This API Is Easy to Integrate

- No JSON payload required, only multipart file upload
- Accepts `.pptx` and `.ppt`
- Returns `application/pdf` directly
- Includes health endpoint (`GET /health`) and root info (`GET /`)
- Works with Swagger at `/docs`

## Robust Handling for Broken Files

When conversion fails, the service does not fail immediately.

It retries conversion using multiple repair methods before returning an error:

1. Direct LibreOffice conversion with several internal conversion strategies
2. PPTX repair method: clean re-zip (junk entry removal and normalization)
3. PPTX repair method: flatten single nested root folder
4. PPTX repair method: store-only re-pack
5. Legacy OLE (`.ppt`) retry path
6. Extension-variant retries (`.pptx` and `.ppt` copies)

If all attempts fail, the API returns `500` with `"Conversion failed"`.

## Quick Start

### 1) Install system dependency

Install LibreOffice and make sure `soffice` or `libreoffice` is available in your PATH.

Ubuntu or Debian:

```bash
sudo apt update
sudo apt install -y libreoffice
```

### 2) Install Python dependencies

```bash
pip install -r requirements.txt
```

### 3) Run the API

```bash
python3 main.py
```

Default URL: `http://127.0.0.1:8000`

## Endpoints

### GET /

Returns basic API metadata:

- service message
- conversion endpoint path
- form field name
- docs path

### GET /health

Returns:

```json
{"status":"ok"}
```

### POST /convert

- Request content type: `multipart/form-data`
- Accepted field names: `file` (primary), `upload` (alias)
- Accepted file extensions: `.pptx`, `.ppt`
- Response content type: `application/pdf`

## Sample Requests

### cURL examples

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
  -F "upload=@./legacy.ppt" \
  --output legacy.pdf
```

</details>

### Python (requests)

```python
import requests

url = "http://127.0.0.1:8000/convert"
with open("slides.pptx", "rb") as f:
    response = requests.post(url, files={"file": f}, timeout=300)

response.raise_for_status()
with open("slides.pdf", "wb") as out:
    out.write(response.content)
```

### Python (httpx)

```python
import httpx

url = "http://127.0.0.1:8000/convert"
with open("slides.ppt", "rb") as f:
    files = {"file": ("slides.ppt", f, "application/vnd.ms-powerpoint")}
    resp = httpx.post(url, files=files, timeout=300)

resp.raise_for_status()
with open("slides.pdf", "wb") as out:
    out.write(resp.content)
```

### JavaScript (Node.js + fetch)

```javascript
import fs from "node:fs";
import FormData from "form-data";
import fetch from "node-fetch";

const form = new FormData();
form.append("file", fs.createReadStream("slides.pptx"));

const response = await fetch("http://127.0.0.1:8000/convert", {
  method: "POST",
  body: form,
  headers: form.getHeaders(),
});

if (!response.ok) {
  throw new Error(`Conversion failed: ${response.status}`);
}

const arrayBuffer = await response.arrayBuffer();
fs.writeFileSync("slides.pdf", Buffer.from(arrayBuffer));
```

### Browser JavaScript

```javascript
const formData = new FormData();
formData.append("file", fileInput.files[0]);

const response = await fetch("http://127.0.0.1:8000/convert", {
  method: "POST",
  body: formData,
});

if (!response.ok) {
  const err = await response.text();
  throw new Error(err);
}

const blob = await response.blob();
const url = URL.createObjectURL(blob);
const a = document.createElement("a");
a.href = url;
a.download = "converted.pdf";
a.click();
URL.revokeObjectURL(url);
```

### PowerShell

```powershell
$uri = "http://127.0.0.1:8000/convert"
$form = @{ file = Get-Item ".\slides.pptx" }
Invoke-WebRequest -Uri $uri -Method Post -Form $form -OutFile "slides.pdf"
```

## Using Swagger UI

1. Start the API with `python3 main.py`
2. Open `http://127.0.0.1:8000/docs`
3. Expand `POST /convert`
4. Click Try it out
5. Select `.pptx` or `.ppt` file and execute
6. Save returned PDF

## Runtime Configuration

You can configure the server with environment variables:

- `API_HOST` (default: `0.0.0.0`)
- `API_PORT` (default: `8000`)
- `API_RELOAD` (`true` or `false`, default: `false`)

Example:

```bash
API_HOST=127.0.0.1 API_PORT=9000 API_RELOAD=true python3 main.py
```

## Error Handling

- `400` when upload is missing or extension is unsupported
- `500` when conversion fails even after all conversion and repair attempts

## Project Structure

- `main.py`: uvicorn launcher
- `app/api.py`: endpoint and request handling
- `app/services/conversion_service.py`: conversion orchestration
- `app/services/libreoffice_converter.py`: conversion strategies
- `app/services/repair_utils.py`: repair strategies
- `app/utils/`: command and file helpers
