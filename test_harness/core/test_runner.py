"""Threaded test executor with retry and callbacks."""

from __future__ import annotations
import logging
import threading
import time
import urllib.error
from typing import Callable

from ..models.test_case import TestCase
from ..models.test_result import TestResult
from .assertions import run_assertions

log = logging.getLogger(__name__)

MAX_RETRIES = 3
BACKOFF_BASE = 1  # seconds


class TestRunner:
    def __init__(self, bridge, on_progress: Callable, on_result: Callable,
                 on_done: Callable, root=None):
        self._bridge = bridge
        self._on_progress = on_progress
        self._on_result = on_result
        self._on_done = on_done
        self._root = root  # Tk root for thread-safe callbacks
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self, cases: list[TestCase]):
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, args=(cases,), daemon=True)
        self._thread.start()

    def stop(self):
        self._stop.set()

    @property
    def running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def _callback(self, fn, *args):
        if self._root:
            self._root.after(0, lambda: fn(*args))
        else:
            fn(*args)

    def _run(self, cases: list[TestCase]):
        total = len(cases)
        for i, tc in enumerate(cases):
            if self._stop.is_set():
                break
            self._callback(self._on_progress, i, total)
            result = self._execute_one(tc)
            self._callback(self._on_result, result)

        self._callback(self._on_done)

    def _execute_one(self, tc: TestCase) -> TestResult:
        endpoint_fn = {
            "calcTaxes": self._bridge.calc_taxes,
            "commit": self._bridge.commit,
            "pCode": self._bridge.pcode_lookup,
            "geocode": self._bridge.geocode,
        }.get(tc.endpoint)

        if endpoint_fn is None:
            return TestResult(tc, status="error", error_message=f"Unknown endpoint: {tc.endpoint}")

        last_exc = None
        for attempt in range(MAX_RETRIES):
            if self._stop.is_set():
                return TestResult(tc, status="skipped")

            t0 = time.perf_counter()
            try:
                resp = endpoint_fn(tc.request_body)
                elapsed = (time.perf_counter() - t0) * 1000

                failures = run_assertions(tc.endpoint, resp, tc.request_body)
                tax_count = self._count_taxes(resp, tc.endpoint)

                return TestResult(
                    test_case=tc,
                    status="fail" if failures else "pass",
                    duration_ms=round(elapsed, 1),
                    response=resp,
                    http_status=200,
                    assertion_details=failures,
                    tax_count=tax_count,
                )
            except urllib.error.HTTPError as exc:
                elapsed = (time.perf_counter() - t0) * 1000
                last_exc = exc
                code = exc.code

                if code == 401:
                    return TestResult(tc, status="error", duration_ms=round(elapsed, 1),
                                     http_status=401,
                                     error_message="401 Unauthorized — check credentials")
                if code >= 500:
                    log.warning("Attempt %d/%d for %s: %s", attempt + 1, MAX_RETRIES,
                                tc.description, exc)
                    time.sleep(BACKOFF_BASE * (2 ** attempt))
                    continue
                # 4xx (not 401) — no retry
                body = ""
                try:
                    body = exc.read().decode()
                except Exception:
                    pass
                return TestResult(tc, status="fail", duration_ms=round(elapsed, 1),
                                  http_status=code,
                                  error_message=f"HTTP {code}: {body}")
            except Exception as exc:
                elapsed = (time.perf_counter() - t0) * 1000
                last_exc = exc
                log.warning("Attempt %d/%d for %s: %s", attempt + 1, MAX_RETRIES,
                            tc.description, exc)
                time.sleep(BACKOFF_BASE * (2 ** attempt))

        return TestResult(tc, status="error",
                          duration_ms=0,
                          error_message=f"All {MAX_RETRIES} retries failed: {last_exc}")

    @staticmethod
    def _count_taxes(resp, endpoint: str) -> int:
        if endpoint != "calcTaxes" or not isinstance(resp, dict):
            return 0
        count = 0
        for inv in resp.get("inv", []):
            for itm in inv.get("itms", []):
                count += len(itm.get("txs", []))
        return count
