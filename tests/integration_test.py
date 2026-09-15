"""Real HTTP integration tests against a running service.

Usage:
    python tests/integration_test.py [BASE_URL]

Starts nothing itself; expects the service to already be running (e.g. started
by GitHub Actions or manually). Sends real multipart HTTP requests and verifies
the returned PDFs are valid and readable.
"""
import concurrent.futures
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures"
BASE_URL = os.getenv("BASE_URL", "http://127.0.0.1:8000")


def wait_until_ready(url, timeout=60):
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url + "/", timeout=5) as resp:
                if resp.status == 200:
                    return True
        except Exception:
            time.sleep(1)
    return False


def post_convert(url, file_path):
    """POST a file to /convert using multipart/form-data via urllib."""
    boundary = "----WebKitFormBoundary7MA4YWxkTrZu0gW"
    filename = Path(file_path).name
    data = file_path.read_bytes()
    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'
        f"Content-Type: application/octet-stream\r\n\r\n"
    ).encode() + data + f"\r\n--{boundary}--\r\n".encode()
    req = urllib.request.Request(
        url + "/convert",
        data=body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        return resp.status, resp.read()


def is_valid_pdf(data: bytes) -> bool:
    return data.startswith(b"%PDF") and b"%%EOF" in data


def main():
    url = BASE_URL
    print(f"Waiting for service at {url} ...")
    if not wait_until_ready(url):
        print("FAIL: service did not become ready")
        return 1

    fixtures = sorted(FIXTURE_DIR.glob("*.pptx"))
    if not fixtures:
        print("FAIL: no fixtures found")
        return 1

    # 1. Sequential conversion of each fixture.
    for fx in fixtures:
        status, data = post_convert(url, fx)
        ok = status == 200 and is_valid_pdf(data)
        print(f"convert {fx.name}: status={status} valid_pdf={ok} size={len(data)}")
        if not ok:
            print(f"FAIL: {fx.name} did not convert to a valid PDF")
            return 1

    # 2. Concurrent conversions to exercise the concurrency limit.
    #    Use more requests than the configured limit.
    limit = int(os.getenv("CONCURRENT_CONVERSIONS", "1"))
    n_requests = max(limit * 3, 6)
    print(f"Running {n_requests} concurrent requests (limit={limit}) ...")
    with concurrent.futures.ThreadPoolExecutor(max_workers=n_requests) as pool:
        futures = [pool.submit(post_convert, url, fixtures[0]) for _ in range(n_requests)]
        results = [f.result() for f in futures]
    for i, (status, data) in enumerate(results):
        ok = status == 200 and is_valid_pdf(data)
        print(f"  concurrent[{i}]: status={status} valid_pdf={ok}")
        if not ok:
            print(f"FAIL: concurrent request {i} failed")
            return 1

    print("ALL INTEGRATION TESTS PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())