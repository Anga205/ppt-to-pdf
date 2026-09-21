"""Document conversion tests."""
from pathlib import Path
from fastapi.testclient import TestClient
import app.api as api_module

client = TestClient(api_module.app)


def test_convert_doc_success(monkeypatch):
    def _fake_convert_document_file(input_path, output_path):
        output_path.write_bytes(b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\ntrailer\n<<>>\n%%EOF\n")
    monkeypatch.setattr(api_module, "convert_document_file", _fake_convert_document_file)
    files = {"file": ("test.docx", b"dummy-docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document")}
    response = client.post("/convert/doc", files=files)
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/pdf")
    assert response.content.startswith(b"%PDF")


def test_convert_doc_unsupported_format():
    files = {"file": ("bad.exe", b"bad", "application/octet-stream")}
    response = client.post("/convert/doc", files=files)
    assert response.status_code == 400
