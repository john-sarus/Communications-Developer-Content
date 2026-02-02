"""Tab 3: JSON sample file tree and preview."""

from __future__ import annotations
import json
import tkinter as tk
from tkinter import ttk, scrolledtext

from ..core.json_loader import list_samples, load_file
from ..models.test_case import TestCase


class SampleBrowser(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self._samples: list[tuple[str, str, dict]] = []
        self._build()
        self._load()

    def _build(self):
        pad = dict(padx=6, pady=3)
        pw = ttk.PanedWindow(self, orient="horizontal")
        pw.pack(fill="both", expand=True, **pad)

        # Left: tree
        left = ttk.Frame(pw)
        pw.add(left, weight=1)
        self._tree = ttk.Treeview(left, selectmode="browse")
        self._tree.heading("#0", text="JSON Samples")
        self._tree.pack(fill="both", expand=True)
        self._tree.bind("<<TreeviewSelect>>", self._on_select)

        # Right: preview
        right = ttk.Frame(pw)
        pw.add(right, weight=2)
        self._preview = scrolledtext.ScrolledText(right, wrap="word", state="disabled",
                                                   font=("Consolas", 9))
        self._preview.pack(fill="both", expand=True)

        # Buttons
        btn = ttk.Frame(self)
        btn.pack(fill="x", **pad)
        ttk.Button(btn, text="Run This Sample", command=self._run_sample).pack(side="left", **pad)
        ttk.Button(btn, text="Use as Base Template", command=self._use_as_template).pack(
            side="left", **pad)
        ttk.Button(btn, text="Refresh", command=self._load).pack(side="right", **pad)

    def _load(self):
        self._tree.delete(*self._tree.get_children())
        self._samples = list_samples()
        cat_nodes: dict[str, str] = {}
        for path, cat, data in self._samples:
            if cat not in cat_nodes:
                cat_nodes[cat] = self._tree.insert("", "end", text=cat, open=False)
            import os
            fname = os.path.basename(path)
            self._tree.insert(cat_nodes[cat], "end", text=fname, values=(path,))

    def _on_select(self, _event=None):
        sel = self._tree.selection()
        if not sel:
            return
        item = sel[0]
        vals = self._tree.item(item, "values")
        if not vals:
            return
        path = vals[0]
        data = load_file(path)
        self._preview.config(state="normal")
        self._preview.delete("1.0", "end")
        if data is not None:
            self._preview.insert("1.0", json.dumps(data, indent=2))
        else:
            self._preview.insert("1.0", "(Could not parse file)")
        self._preview.config(state="disabled")

    def _selected_data(self) -> tuple[str, dict | list | None]:
        sel = self._tree.selection()
        if not sel:
            return "", None
        vals = self._tree.item(sel[0], "values")
        if not vals:
            return "", None
        path = vals[0]
        return path, load_file(path)

    def _run_sample(self):
        path, data = self._selected_data()
        if data is None:
            return
        endpoint = "calcTaxes"
        if isinstance(data, list):
            endpoint = "geocode"
        elif isinstance(data, dict):
            if "doc" in data and "cmmt" in data:
                endpoint = "commit"
            elif "CountryIso" in data or "NpaNxx" in data:
                endpoint = "pCode"

        tc = TestCase(id=0, endpoint=endpoint, description=f"Sample: {path}",
                      request_body=data, source_file=path)
        self.app.run_tests([tc])

    def _use_as_template(self):
        _, data = self._selected_data()
        if data and isinstance(data, dict):
            self.app.base_template = data
