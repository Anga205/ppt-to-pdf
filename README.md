# PPT/PPTX to PDF API

A HTTP service that converts PowerPoint files to PDF, the concept is very simple:
- One main endpoint: `POST /convert`
- Accepts `.pptx`, `.ppt`, and `.pdf` (PDF passthrough)
- Returns `application/pdf` directly
- Upload one file and receive one PDF

It even works with broken pptx files or ppt files that were made in very old and possibly outdated versions of powerpoint (like the ones on [pesuacademy](pesuacademy.com))


<details>
<summary>Click here to read about how the API handles broken files</summary>

---

When conversion fails, the service does not fail immediately.

It retries conversion using multiple repair methods before returning an error:

1. Direct LibreOffice conversion with several internal conversion strategies
2. PPTX repair method: clean re-zip (junk entry removal and normalization)
3. PPTX repair method: flatten single nested root folder
4. PPTX repair method: store-only re-pack
5. Legacy OLE (`.ppt`) retry path
6. Extension-variant retries (`.pptx` and `.ppt` copies)

If all attempts fail, the API returns `500` with `"Conversion failed"`.

---
</details>

## Endpoints

### GET /

Returns an HTML wrapper page that uploads files and calls `POST /convert`.
The page clearly indicates it is only a wrapper around the main API.
It also links to:

- Swagger UI docs (`/docs`)
- GitHub repository

### POST /convert

- Request content type: `multipart/form-data`
- Accepted field names: `file` (primary), `upload` (alias)
- Accepted file extensions: `.pptx`, `.ppt`, `.pdf`
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


### cURL / bash


```bash
curl -X POST "http://127.0.0.1:8000/convert" \
  -F "file=@./slides.pptx" \
  --output slides-from-container.pdf
```