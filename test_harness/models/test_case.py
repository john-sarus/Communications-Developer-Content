"""Test case data model."""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any


@dataclass
class TestCase:
    id: int
    endpoint: str  # e.g. "calcTaxes", "commit", "pCode", "geocode"
    description: str
    request_body: dict[str, Any]
    # Matrix dimension values that produced this case (for display/filtering)
    dimensions: dict[str, Any] = field(default_factory=dict)
    # Source JSON file path if loaded from a sample
    source_file: str | None = None

    @property
    def key(self) -> str:
        """Stable string key for snapshot comparison."""
        parts = [self.endpoint]
        for k in sorted(self.dimensions):
            parts.append(f"{k}={self.dimensions[k]}")
        return "|".join(parts)
