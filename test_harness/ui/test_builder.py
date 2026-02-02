"""Tab 2: Matrix dimension selectors and test generation."""

from __future__ import annotations
import tkinter as tk
from tkinter import ttk, messagebox

from ..core.matrix_engine import (
    COMMON_PCODES, CUSTOMER_TYPES, SALE_TYPES, DISCOUNT_TYPES,
    EXEMPTION_SCENARIOS, OVERRIDE_SCENARIOS, generate,
)


class TestBuilder(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self._ts_pairs: list[tuple[int, int]] = []
        self._build()

    def _build(self):
        pad = dict(padx=6, pady=3)

        top = ttk.Frame(self)
        top.pack(fill="both", expand=True, **pad)

        # Left: TS pairs listbox
        left = ttk.LabelFrame(top, text="Transaction/Service Pairs")
        left.pack(side="left", fill="both", expand=True, **pad)

        self._ts_listbox = tk.Listbox(left, selectmode="extended", width=30, height=18)
        self._ts_listbox.pack(fill="both", expand=True, **pad)
        sb = ttk.Scrollbar(left, orient="vertical", command=self._ts_listbox.yview)
        sb.pack(side="right", fill="y")
        self._ts_listbox.config(yscrollcommand=sb.set)
        ttk.Label(left, text="(Populated after connection)").pack()

        # Right column
        right = ttk.Frame(top)
        right.pack(side="left", fill="both", expand=True, **pad)

        # Customer types
        ct_frame = ttk.LabelFrame(right, text="Customer Type")
        ct_frame.pack(fill="x", **pad)
        self._cust_vars: dict[str, tk.BooleanVar] = {}
        for name in CUSTOMER_TYPES:
            v = tk.BooleanVar(value=(name == "Residential"))
            ttk.Checkbutton(ct_frame, text=name, variable=v).pack(anchor="w")
            self._cust_vars[name] = v

        # Sale types
        st_frame = ttk.LabelFrame(right, text="Sale Type")
        st_frame.pack(fill="x", **pad)
        self._sale_vars: dict[str, tk.BooleanVar] = {}
        for name in SALE_TYPES:
            v = tk.BooleanVar(value=(name == "Retail"))
            ttk.Checkbutton(st_frame, text=name, variable=v).pack(anchor="w")
            self._sale_vars[name] = v

        # Discount types
        dt_frame = ttk.LabelFrame(right, text="Discount Type")
        dt_frame.pack(fill="x", **pad)
        self._disc_vars: dict[str, tk.BooleanVar] = {}
        for name in DISCOUNT_TYPES:
            v = tk.BooleanVar(value=(name == "None"))
            ttk.Checkbutton(dt_frame, text=name, variable=v).pack(anchor="w")
            self._disc_vars[name] = v

        # Flags
        fl_frame = ttk.LabelFrame(right, text="Flags")
        fl_frame.pack(fill="x", **pad)
        self._flag_vars: dict[str, tk.BooleanVar] = {}
        for flag in ("tax_inclusive", "proration", "adjustment", "lifeline",
                      "summarize", "invoice_mode"):
            v = tk.BooleanVar(value=False)
            ttk.Checkbutton(fl_frame, text=flag.replace("_", " ").title(),
                            variable=v).pack(anchor="w")
            self._flag_vars[flag] = v

        # Exemption / Override
        eo_frame = ttk.Frame(right)
        eo_frame.pack(fill="x", **pad)

        exm_frame = ttk.LabelFrame(eo_frame, text="Exemptions")
        exm_frame.pack(side="left", fill="x", expand=True, **pad)
        self._exm_vars: dict[str, tk.BooleanVar] = {}
        for name in EXEMPTION_SCENARIOS:
            v = tk.BooleanVar(value=(name == "None"))
            ttk.Checkbutton(exm_frame, text=name, variable=v).pack(anchor="w")
            self._exm_vars[name] = v

        ovr_frame = ttk.LabelFrame(eo_frame, text="Overrides")
        ovr_frame.pack(side="left", fill="x", expand=True, **pad)
        self._ovr_vars: dict[str, tk.BooleanVar] = {}
        for name in OVERRIDE_SCENARIOS:
            v = tk.BooleanVar(value=(name == "None"))
            ttk.Checkbutton(ovr_frame, text=name, variable=v).pack(anchor="w")
            self._ovr_vars[name] = v

        # Jurisdictions
        jur_frame = ttk.LabelFrame(self, text="Jurisdictions (PCodes)")
        jur_frame.pack(fill="x", **pad)
        self._pcode_var = tk.StringVar()
        ttk.Entry(jur_frame, textvariable=self._pcode_var, width=60).pack(side="left", **pad)
        ttk.Button(jur_frame, text="Add Common", command=self._add_common).pack(side="left", **pad)

        # Bottom: count + generate
        bot = ttk.Frame(self)
        bot.pack(fill="x", **pad)
        self._count_label = ttk.Label(bot, text="0 test cases")
        self._count_label.pack(side="left", **pad)

        ttk.Label(bot, text="Cap:").pack(side="left")
        self._cap_var = tk.IntVar(value=500)
        ttk.Spinbox(bot, from_=1, to=10000, textvariable=self._cap_var,
                     width=6).pack(side="left", **pad)

        ttk.Button(bot, text="Generate & Run", command=self._generate_and_run).pack(
            side="right", **pad)
        ttk.Button(bot, text="Count", command=self._update_count).pack(side="right", **pad)

    def populate_ts_pairs(self, pairs: list[dict]):
        self._ts_listbox.delete(0, "end")
        self._ts_pairs.clear()
        for p in pairs:
            tran = p.get("TransactionType", p.get("tran", 0))
            serv = p.get("ServiceType", p.get("serv", 0))
            desc = p.get("TransactionDescription", p.get("desc", ""))
            self._ts_pairs.append((tran, serv))
            self._ts_listbox.insert("end", f"{tran}/{serv} — {desc}")

    def _add_common(self):
        existing = self._pcode_var.get().strip()
        codes = ", ".join(str(p) for p in COMMON_PCODES)
        if existing:
            self._pcode_var.set(existing + ", " + codes)
        else:
            self._pcode_var.set(codes)

    def _get_selected_ts(self) -> list[tuple[int, int]]:
        sel = self._ts_listbox.curselection()
        if not sel:
            return []
        return [self._ts_pairs[i] for i in sel]

    def _get_pcodes(self) -> list[int]:
        raw = self._pcode_var.get().strip()
        if not raw:
            return []
        result = []
        for tok in raw.replace(";", ",").split(","):
            tok = tok.strip()
            if tok.isdigit():
                result.append(int(tok))
        return result

    def _gather_params(self):
        ts = self._get_selected_ts()
        custs = [CUSTOMER_TYPES[n] for n, v in self._cust_vars.items() if v.get()]
        sales = [SALE_TYPES[n] for n, v in self._sale_vars.items() if v.get()]
        discs = [DISCOUNT_TYPES[n] for n, v in self._disc_vars.items() if v.get()]
        pcodes = self._get_pcodes()
        exms = [EXEMPTION_SCENARIOS[n] for n, v in self._exm_vars.items() if v.get()]
        ovrs = [OVERRIDE_SCENARIOS[n] for n, v in self._ovr_vars.items() if v.get()]
        flags = {k: v.get() for k, v in self._flag_vars.items()}
        return ts, custs, sales, discs, pcodes, exms, ovrs, flags

    def _update_count(self):
        ts, custs, sales, discs, pcodes, exms, ovrs, _ = self._gather_params()
        if not ts or not pcodes:
            self._count_label.config(text="Select TS pairs and PCodes")
            return
        total = len(ts) * len(custs) * len(sales) * len(discs) * len(pcodes) * len(exms) * len(ovrs)
        cap = self._cap_var.get()
        if total > cap:
            self._count_label.config(text=f"{total} combinations → capped at {cap}")
        else:
            self._count_label.config(text=f"{total} test cases")

    def _generate_and_run(self):
        ts, custs, sales, discs, pcodes, exms, ovrs, flags = self._gather_params()
        if not ts:
            messagebox.showwarning("Missing", "Select at least one TS pair.")
            return
        if not pcodes:
            messagebox.showwarning("Missing", "Enter at least one PCode.")
            return

        cases = generate(ts, custs, sales, discs, pcodes, exms, ovrs, flags,
                         cap=self._cap_var.get())
        self.app.run_tests(cases)
