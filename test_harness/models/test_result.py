"""Test result data model."""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any

from .test_case import TestCase


@dataclass
class TestResult:
    test_case: TestCase
    status: str  # "pass", "fail", "error", "skipped"
    duration_ms: float = 0.0
    response: dict[str, Any] | list | None = None
    http_status: int = 0
    assertion_details: list[str] = field(default_factory=list)
    error_message: str = ""
    tax_count: int = 0

    def to_dict(self) -> dict:
        return {
            "test_case_id": self.test_case.id,
            "endpoint": self.test_case.endpoint,
            "key": self.test_case.key,
            "status": self.status,
            "duration_ms": self.duration_ms,
            "http_status": self.http_status,
            "assertion_details": self.assertion_details,
            "error_message": self.error_message,
            "tax_count": self.tax_count,
            "request": self.test_case.request_body,
            "response": self.response,
            "dimensions": self.test_case.dimensions,
        }
