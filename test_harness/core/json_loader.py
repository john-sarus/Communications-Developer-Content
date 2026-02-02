"""Load existing JSON sample files from the repo."""

from __future__ import annotations
import json
import os
from typing import Any

_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
_JSON_DIR = os.path.join(_REPO_ROOT, "afc_saaspro_tax", "afc_rest_apis", "JSON")


def list_samples(root: str | None = None) -> list[tuple[str, str, Any]]:
    """Walk JSON directory and return (path, category, parsed_json) tuples."""
    root = root or _JSON_DIR
    results = []
    if not os.path.isdir(root):
        return results
    for dirpath, _, filenames in os.walk(root):
        for fn in sorted(filenames):
            if not fn.lower().endswith(".json"):
                continue
            full = os.path.join(dirpath, fn)
            rel = os.path.relpath(full, root)
            cat = os.path.dirname(rel) or "root"
            try:
                with open(full, encoding="utf-8") as f:
                    data = json.load(f)
                results.append((full, cat, data))
            except (json.JSONDecodeError, OSError):
                continue
    return results


def load_file(path: str) -> dict | list | None:
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return None
