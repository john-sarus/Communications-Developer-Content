"""Combinatorial test case generation."""

from __future__ import annotations
import copy
import itertools
import random
from typing import Any

from ..models.test_case import TestCase

# Representative US/CA PCodes
COMMON_PCODES = [
    4133800,   # Seattle WA
    253500,    # Los Angeles CA
    2757800,   # New York NY
    611200,    # Chicago IL
    4012200,   # Dallas TX
    621400,    # Indianapolis IN
    872800,    # Denver CO
    880600,    # Miami FL
    1703400,   # Atlanta GA
    4400000,   # Canada (Ontario)
]

CUSTOMER_TYPES = {"Residential": 0, "Business": 1, "Senior Citizen": 2, "Industrial": 3}
SALE_TYPES = {"Wholesale": 0, "Retail": 1, "Consumed": 2, "VendorUse": 3}
DISCOUNT_TYPES = {"None": 0, "RetailProduct": 1, "ManufacturerProduct": 2,
                  "AccountLevel": 3, "Subsidized": 4, "Goodwill": 5}
EXEMPTION_SCENARIOS = {"None": None, "Category": "cat", "TaxType": "tpe", "Level": "lvl"}
OVERRIDE_SCENARIOS = {"None": None, "SafeHarbor": "sh", "TaxOverride": "ovr"}

DEFAULT_COMPANY = {
    "bscl": 1, "svcl": 0, "fclt": True, "frch": True, "reg": False
}


def _build_exemption(scenario: str | None, pcd: int) -> list | None:
    if scenario is None:
        return None
    if scenario == "cat":
        return [{"loc": {"pcd": pcd}, "cat": 1, "dom": 0, "scp": 0}]
    if scenario == "tpe":
        return [{"loc": {"pcd": pcd}, "tpe": 1, "lvl": 1, "dom": 0, "scp": 0}]
    if scenario == "lvl":
        return [{"loc": {"pcd": pcd}, "tpe": 1, "lvl": 0, "dom": 0, "scp": 0, "frc": True}]
    return None


def _build_overrides(scenario: str | None) -> tuple[list | None, list | None]:
    """Returns (tax_overrides, safe_harbor_overrides)."""
    if scenario is None:
        return None, None
    if scenario == "sh":
        return None, [{"sh": 1, "old": 37.1, "new": 40.0}]
    if scenario == "ovr":
        return [{"loc": {"st": "WA", "ctry": "USA"}, "scp": 1, "tid": 1, "lvl": 1,
                 "lvlExm": True, "brkt": [{"rate": 0.05, "max": 9999999}]}], None
    return None, None


def generate(
    ts_pairs: list[tuple[int, int]],
    customer_types: list[int],
    sale_types: list[int],
    discount_types: list[int],
    pcodes: list[int],
    exemption_scenarios: list[str | None],
    override_scenarios: list[str | None],
    flags: dict[str, bool],
    cap: int = 500,
    base_template: dict | None = None,
) -> list[TestCase]:
    """Generate test cases from combinatorial matrix, capped with stratified sampling."""

    dims = [ts_pairs, customer_types, sale_types, discount_types,
            pcodes, exemption_scenarios, override_scenarios]
    combos = list(itertools.product(*dims))

    if len(combos) > cap:
        combos = _stratified_sample(combos, dims, cap)

    company = (base_template or {}).get("cmpn", DEFAULT_COMPANY)
    cases: list[TestCase] = []

    for idx, (ts, cust, sale, disc, pcd, exm_scen, ovr_scen) in enumerate(combos):
        tran, serv = ts
        line_item: dict[str, Any] = {
            "ref": f"L{idx}",
            "from": {"pcd": pcd},
            "to": {"pcd": pcd},
            "chg": 100.00,
            "line": 1,
            "tran": tran,
            "serv": serv,
            "sale": sale,
            "disc": disc,
        }
        if flags.get("tax_inclusive"):
            line_item["incl"] = True
        if flags.get("proration"):
            line_item["pror"] = 0.5
            line_item["proadj"] = 1
        if flags.get("adjustment"):
            line_item["adj"] = True

        invoice: dict[str, Any] = {
            "doc": f"TEST-{idx:05d}",
            "bill": {"pcd": pcd},
            "cust": cust,
            "date": "2025-01-15T00:00:00Z",
            "itms": [line_item],
            "dtl": True,
            "summ": flags.get("summarize", False),
        }
        if flags.get("lifeline"):
            invoice["lfln"] = True
        if "invoice_mode" in flags:
            invoice["invm"] = flags["invoice_mode"]

        exms = _build_exemption(exm_scen, pcd)
        if exms:
            invoice["exms"] = exms

        ovr, sovr = _build_overrides(ovr_scen)
        request: dict[str, Any] = {"cmpn": copy.deepcopy(company), "inv": [invoice]}
        if ovr:
            request["ovr"] = ovr
        if sovr:
            request["sovr"] = sovr

        desc = f"T/S={tran}/{serv} cust={cust} sale={sale} pcd={pcd}"
        cases.append(TestCase(
            id=idx,
            endpoint="calcTaxes",
            description=desc,
            request_body=request,
            dimensions={
                "tran": tran, "serv": serv, "cust": cust, "sale": sale,
                "disc": disc, "pcd": pcd, "exemption": exm_scen, "override": ovr_scen,
            },
        ))

    return cases


def _stratified_sample(combos, dims, cap) -> list:
    """Sample ensuring every dimension value appears at least once."""
    random.seed(42)
    selected = set()
    result = []

    # First pass: ensure coverage
    for dim_idx, dim_vals in enumerate(dims):
        for val in dim_vals:
            for combo in combos:
                if combo[dim_idx] == val and id(combo) not in selected:
                    selected.add(id(combo))
                    result.append(combo)
                    break

    # Fill remaining with random
    remaining = [c for c in combos if id(c) not in selected]
    random.shuffle(remaining)
    result.extend(remaining[:max(0, cap - len(result))])

    return result[:cap]
