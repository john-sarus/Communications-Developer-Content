"""Structural validators for API responses."""

from __future__ import annotations
from typing import Any


def validate_calc_taxes(response: dict | None, request: dict) -> list[str]:
    """Return list of failure messages (empty = pass)."""
    failures: list[str] = []

    if response is None:
        return ["Response is None"]

    inv = response.get("inv")
    if not isinstance(inv, list) or len(inv) == 0:
        failures.append("Response missing 'inv' list or empty")
        return failures

    errs = response.get("err")
    if errs:
        failures.append(f"Top-level errors: {errs}")

    req_invoices = request.get("inv", [])
    for i, inv_result in enumerate(inv):
        prefix = f"inv[{i}]"

        inv_errs = inv_result.get("err")
        if inv_errs:
            failures.append(f"{prefix} errors: {inv_errs}")

        itms = inv_result.get("itms")
        if itms is None:
            failures.append(f"{prefix} missing 'itms'")
            continue

        # Check line count matches request
        if i < len(req_invoices):
            req_items = req_invoices[i].get("itms", [])
            if len(itms) != len(req_items):
                failures.append(
                    f"{prefix} item count mismatch: got {len(itms)}, expected {len(req_items)}")

        for j, item in enumerate(itms):
            ip = f"{prefix}.itms[{j}]"
            item_errs = item.get("err")
            if item_errs:
                failures.append(f"{ip} errors: {item_errs}")

            txs = item.get("txs")
            if txs is None:
                failures.append(f"{ip} missing 'txs'")
                continue

            for k, tax in enumerate(txs):
                tp = f"{ip}.txs[{k}]"
                rate = tax.get("rate")
                if rate is not None and (rate < 0.0 or rate > 1.0):
                    failures.append(f"{tp} rate out of range: {rate}")
                if tax.get("tax") is None:
                    failures.append(f"{tp} missing 'tax' amount")
                if tax.get("tid") is None:
                    failures.append(f"{tp} missing 'tid'")
                if tax.get("lvl") is None:
                    failures.append(f"{tp} missing 'lvl'")

        # Summarized taxes check
        if i < len(req_invoices) and req_invoices[i].get("summ"):
            if not inv_result.get("summ"):
                failures.append(f"{prefix} requested summ=True but no 'summ' in result")

    return failures


def validate_commit(response: dict | None) -> list[str]:
    if response is None:
        return ["Response is None"]
    if not response.get("ok"):
        errs = response.get("err", [])
        return [f"Commit not ok: {errs}"]
    return []


def validate_pcode_lookup(response: dict | None) -> list[str]:
    if response is None:
        return ["Response is None"]
    loc_data = response.get("LocationData")
    if not loc_data:
        return ["LocationData empty or missing"]
    match_count = response.get("MatchCount", 0)
    if match_count <= 0:
        return [f"MatchCount is {match_count}"]
    return []


def validate_geocode(response: list | None) -> list[str]:
    if response is None:
        return ["Response is None"]
    if not isinstance(response, list) or len(response) == 0:
        return ["Geocode response empty"]
    failures = []
    for i, r in enumerate(response):
        if r.get("err"):
            failures.append(f"geocode[{i}] error: {r['err']}")
        if r.get("pcd") is None:
            failures.append(f"geocode[{i}] missing pcd")
        if r.get("lat") is None or r.get("long") is None:
            failures.append(f"geocode[{i}] missing lat/long")
    return failures


VALIDATORS = {
    "calcTaxes": validate_calc_taxes,
    "commit": validate_commit,
    "pCode": validate_pcode_lookup,
    "geocode": validate_geocode,
}


def run_assertions(endpoint: str, response: Any, request: Any = None) -> list[str]:
    fn = VALIDATORS.get(endpoint)
    if fn is None:
        return []
    if endpoint == "calcTaxes":
        return fn(response, request)
    return fn(response)
