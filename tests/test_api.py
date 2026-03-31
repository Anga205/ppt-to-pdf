from pathlib import Path

from fastapi.testclient import TestClient

import app.api as api_module


client = TestClient(api_module.app)


def _write_fake_pdf(output_path: Path):
    output_path.write_bytes(
        b"%PDF-1.4\n"
        b"1 0 obj\n"
        b"<< /Type /Catalog >>\n"
        b"endobj\n"
        b"trailer\n"
        b"<<>>\n"
        b"%%EOF\n"
    )


def _fake_convert_file(_input_path, output_path):
    _write_fake_pdf(output_path)


def test_root_endpoint():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["endpoint"] == "POST /convert"


def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_convert_success_with_file_field(monkeypatch):
    monkeypatch.setattr(api_module, "convert_file", _fake_convert_file)
    files = {
        "file": (
            "slides.pptx",
            b"dummy-pptx-content",
            "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        )
    }
    response = client.post("/convert", files=files)
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/pdf")
    assert response.headers["content-disposition"].endswith("slides.pdf\"")
    assert response.content.startswith(b"%PDF")


def test_convert_success_with_upload_alias(monkeypatch):
    monkeypatch.setattr(api_module, "convert_file", _fake_convert_file)
    files = {
        "upload": (
            "legacy.ppt",
            b"dummy-ppt-content",
            "application/vnd.ms-powerpoint",
        )
    }
    response = client.post("/convert", files=files)
    assert response.status_code == 200
    assert response.content.startswith(b"%PDF")


def test_convert_rejects_invalid_extension():
    files = {"file": ("notes.txt", b"not a ppt", "text/plain")}
    response = client.post("/convert", files=files)
    assert response.status_code == 400
    assert response.json()["detail"] == "Only .ppt and .pptx files are supported"


def test_convert_missing_upload_returns_400():
    response = client.post("/convert")
    assert response.status_code == 400
    assert "Missing upload" in response.json()["detail"]
