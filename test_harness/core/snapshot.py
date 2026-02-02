"""Save, load, and diff response snapshots."""

from __future__ import annotations
import json
import os
import uuid
from datetime import datetime
from typing import Any

from ..models.test_result import TestResult

_SNAP_DIR = os.path.join(os.path.dirname(__file__), "..", "snapshots")


def save_snapshot(results: list[TestResult], tag: str = "") -> str:
    os.makedirs(_SNAP_DIR, exist_ok=True)
    run_id = uuid.uuid4().hex[:8]
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    name = f"{run_id}_{ts}"
    if tag:
        name += f"_{tag}"
    path = os.path.join(_SNAP_DIR, f"{name}.json")
    data = {
        "run_id": run_id,
        "timestamp": ts,
        "tag": tag,
        "results": [r.to_dict() for r in results],
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, default=str)
    return path


def load_snapshot(path: str) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def list_snapshots() -> list[str]:
    os.makedirs(_SNAP_DIR, exist_ok=True)
    return sorted(
        [os.path.join(_SNAP_DIR, f) for f in os.listdir(_SNAP_DIR) if f.endswith(".json")],
        reverse=True,
    )


def diff_snapshots(path_a: str, path_b: str) -> list[dict[str, Any]]:
    """Compare two snapshots by test case key. Returns list of difference dicts."""
    a = load_snapshot(path_a)
    b = load_snapshot(path_b)

    a_by_key = {r["key"]: r for r in a["results"]}
    b_by_key = {r["key"]: r for r in b["results"]}

    all_keys = sorted(set(a_by_key) | set(b_by_key))
    diffs = []

    for key in all_keys:
        ra = a_by_key.get(key)
        rb = b_by_key.get(key)

        if ra is None:
            diffs.append({"key": key, "change": "added_in_b", "b": rb})
            continue
        if rb is None:
            diffs.append({"key": key, "change": "removed_in_b", "a": ra})
            continue

        changes = {}
        if ra["status"] != rb["status"]:
            changes["status"] = (ra["status"], rb["status"])
        if ra["tax_count"] != rb["tax_count"]:
            changes["tax_count"] = (ra["tax_count"], rb["tax_count"])

        # Compare tax rates/amounts if both have calcTaxes responses
        a_taxes = _extract_taxes(ra.get("response"))
        b_taxes = _extract_taxes(rb.get("response"))
        if a_taxes != b_taxes:
            changes["taxes_changed"] = True

        if changes:
            diffs.append({"key": key, "change": "modified", "details": changes})

    return diffs


def _extract_taxes(resp) -> list[tuple]:
    if not isinstance(resp, dict):
        return []
    taxes = []
    for inv in resp.get("inv", []):
        for itm in inv.get("itms", []):
            for tx in itm.get("txs", []):
                taxes.append((tx.get("tid"), tx.get("lvl"), tx.get("rate"), tx.get("tax")))
    return sorted(taxes)
