"""Concurrency limiting for conversions.

Reads the CONCURRENT_CONVERSIONS environment variable (default 1) and exposes
a context manager that acquires a conversion slot. Requests wait (never reject)
until a slot is available. Slots are always released, even on failure.
"""
import logging
import os
import threading
from contextlib import contextmanager

logger = logging.getLogger(__name__)

_DEFAULT_CONCURRENT = 1


def get_concurrent_limit() -> int:
    """Return the configured maximum number of simultaneous conversions."""
    raw = os.getenv("CONCURRENT_CONVERSIONS")
    if raw is None or raw.strip() == "":
        return _DEFAULT_CONCURRENT
    try:
        value = int(raw)
    except ValueError:
        logger.warning(
            "Invalid CONCURRENT_CONVERSIONS=%r, falling back to %d",
            raw,
            _DEFAULT_CONCURRENT,
        )
        return _DEFAULT_CONCURRENT
    if value < 1:
        logger.warning(
            "CONCURRENT_CONVERSIONS=%d is invalid, falling back to %d",
            value,
            _DEFAULT_CONCURRENT,
        )
        return _DEFAULT_CONCURRENT
    return value


class ConversionLimiter:
    """A simple counting semaphore that never rejects, only waits."""

    def __init__(self, limit: int):
        self._limit = max(1, limit)
        self._semaphore = threading.BoundedSemaphore(self._limit)
        self._active = 0
        self._lock = threading.Lock()

    @property
    def limit(self) -> int:
        return self._limit

    @property
    def active(self) -> int:
        with self._lock:
            return self._active

    @contextmanager
    def slot(self):
        """Acquire a conversion slot, guaranteeing release on exit."""
        self._semaphore.acquire()
        with self._lock:
            self._active += 1
        try:
            yield
        finally:
            with self._lock:
                self._active -= 1
            self._semaphore.release()


# Module-level singleton so all callers share one limiter.
_limiter = None
_limiter_lock = threading.Lock()


def get_limiter() -> ConversionLimiter:
    """Return the process-wide conversion limiter (rebuilt if env changes)."""
    global _limiter
    limit = get_concurrent_limit()
    with _limiter_lock:
        if _limiter is None or _limiter.limit != limit:
            _limiter = ConversionLimiter(limit)
        return _limiter


def reset_limiter():
    """Reset the singleton (used by tests)."""
    global _limiter
    with _limiter_lock:
        _limiter = None