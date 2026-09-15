"""Tests for the conversion concurrency limiter."""
import os
import threading
import time
from pathlib import Path

import pytest

from app.concurrency import (
    ConversionLimiter,
    get_concurrent_limit,
    get_limiter,
    reset_limiter,
)
from app.services import conversion_service


def test_default_limit_is_one(monkeypatch):
    monkeypatch.delenv("CONCURRENT_CONVERSIONS", raising=False)
    assert get_concurrent_limit() == 1


def test_limit_reads_env(monkeypatch):
    monkeypatch.setenv("CONCURRENT_CONVERSIONS", "4")
    assert get_concurrent_limit() == 4


def test_limit_invalid_falls_back(monkeypatch):
    monkeypatch.setenv("CONCURRENT_CONVERSIONS", "abc")
    assert get_concurrent_limit() == 1
    monkeypatch.setenv("CONCURRENT_CONVERSIONS", "0")
    assert get_concurrent_limit() == 1
    monkeypatch.setenv("CONCURRENT_CONVERSIONS", "-3")
    assert get_concurrent_limit() == 1


def test_limiter_never_exceeds_limit():
    limiter = ConversionLimiter(2)
    active = []
    lock = threading.Lock()
    max_active = [0]

    def worker():
        with limiter.slot():
            with lock:
                active.append(1)
                max_active[0] = max(max_active[0], len(active))
            time.sleep(0.05)
            with lock:
                active.pop()

    threads = [threading.Thread(target=worker) for _ in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert max_active[0] <= 2


def test_limiter_releases_on_exception():
    limiter = ConversionLimiter(1)
    with pytest.raises(RuntimeError):
        with limiter.slot():
            raise RuntimeError("boom")
    # Slot must be released after the exception.
    acquired = []
    t = threading.Thread(target=lambda: (limiter.slot().__enter__(), acquired.append(1)))
    t.start()
    t.join(timeout=2)
    assert acquired == [1]


def test_limiter_waits_when_full():
    limiter = ConversionLimiter(1)
    release = threading.Event()
    entered = []

    def hold():
        with limiter.slot():
            entered.append(1)
            release.wait()

    holder = threading.Thread(target=hold)
    holder.start()
    # Wait until the slot is taken.
    deadline = time.time() + 2
    while not entered and time.time() < deadline:
        time.sleep(0.01)
    assert entered == [1]

    # A second acquisition must block until release.
    second_entered = []
    second = threading.Thread(target=lambda: (limiter.slot().__enter__(), second_entered.append(1)))
    second.start()
    time.sleep(0.1)
    assert second_entered == []  # still waiting
    release.set()
    holder.join(timeout=2)
    second.join(timeout=2)
    assert second_entered == [1]


def test_convert_file_uses_limiter(monkeypatch):
    """convert_file must acquire a slot for the whole conversion."""
    calls = []
    monkeypatch.setattr(conversion_service, "_convert_file_unlimited", lambda i, o: calls.append("convert") or o)
    monkeypatch.setattr(conversion_service, "get_limiter", lambda: ConversionLimiter(1))
    out = Path("/tmp/out.pdf")
    conversion_service.convert_file(Path("/tmp/in.pptx"), out)
    assert calls == ["convert"]


def test_convert_file_releases_slot_on_failure(monkeypatch):
    def boom(_i, _o):
        raise RuntimeError("fail")

    monkeypatch.setattr(conversion_service, "_convert_file_unlimited", boom)
    monkeypatch.setattr(conversion_service, "get_limiter", lambda: ConversionLimiter(1))
    with pytest.raises(RuntimeError):
        conversion_service.convert_file(Path("/tmp/in.pptx"), Path("/tmp/out.pdf"))
    # Limiter should have no active slots left.
    assert conversion_service.get_limiter().active == 0