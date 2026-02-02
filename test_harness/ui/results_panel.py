"""Tab 5: Results treeview, detail pane, export."""

from __future__ import annotations
import csv
import json
import os
import tkinter as tk
from tkinter import ttk, scrolledtext, filedialog, messagebox

from ..models.test_result import TestResult
from ..core.snapshot import save_snapshot, list_snapshots, diff_snapshots


class ResultsPanel(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self._results: list[TestResult] = []
        self._build()

    def _build(self):
        pad = dict(padx=6, pady=3)

        pw = ttk.PanedWindow(self, orient="vertical")
        pw.pack(fill="both", expand=True, **pad)

        # Top: treeview
        top = ttk.Frame(pw)
        pw.add(top, weight=2)

        cols = ("id", "endpoint", "ts_pair", "jurisdiction", "status", "duration", "tax_count")
        self._tree = ttk.Treeview(top, columns=cols, show="headings", selectmode="browse")
        for col, hdr, w in [
            ("id", "#", 40), ("endpoint", "Endpoint", 80), ("ts_pair", "TS Pair", 80),
            ("jurisdiction", "Jurisdiction", 90), ("status", "Status", 60),
            ("duration", "Duration(ms)", 90), ("tax_count", "Tax Count", 70),
        ]:
            self._tree.heading(col, text=hdr)
            self._tree.column(col, width=w, anchor="center")

        self._tree.tag_configure("pass", background="#d4edda")
        self._tree.tag_configure("fail", background="#f8d7da")
        self._tree.tag_configure("error", background="#fff3cd")

        sb = ttk.Scrollbar(top, orient="vertical", command=self._tree.yview)
        self._tree.config(yscrollcommand=sb.set)
        self._tree.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")
        self._tree.bind("<<TreeviewSelect>>", self._on_select)

        # Bottom: detail
        bot = ttk.Frame(pw)
        pw.add(bot, weight=1)
        nb = ttk.Notebook(bot)
        nb.pack(fill="both", expand=True)

        self._req_text = scrolledtext.ScrolledText(nb, wrap="word", state="disabled",
                                                    font=("Consolas", 9))
        nb.add(self._req_text, text="Request")

        self._resp_text = scrolledtext.ScrolledText(nb, wrap="word", state="disabled",
                                                     font=("Consolas", 9))
        nb.add(self._resp_text, text="Response")

        self._assert_text = scrolledtext.ScrolledText(nb, wrap="word", state="disabled",
                                                       font=("Consolas", 9))
        nb.add(self._assert_text, text="Assertions")

        # Buttons
        btn_frame = ttk.Frame(self)
        btn_frame.pack(fill="x", **pad)
        ttk.Button(btn_frame, text="Export CSV", command=self._export_csv).pack(side="left", **pad)
        ttk.Button(btn_frame, text="Export JSON", command=self._export_json).pack(side="left", **pad)
        ttk.Button(btn_frame, text="Save Snapshot", command=self._save_snapshot).pack(
            side="left", **pad)
        ttk.Button(btn_frame, text="Compare Snapshots", command=self._compare).pack(
            side="left", **pad)

        # Summary label
        self._summary = ttk.Label(btn_frame, text="")
        self._summary.pack(side="right", **pad)

    def clear(self):
        self._results.clear()
        self._tree.delete(*self._tree.get_children())
        self._summary.config(text="")

    def add_result(self, result: TestResult):
        self._results.append(result)
        dims = result.test_case.dimensions
        ts = f"{dims.get('tran', '?')}/{dims.get('serv', '?')}"
        pcd = str(dims.get("pcd", ""))
        self._tree.insert("", "end", values=(
            result.test_case.id, result.test_case.endpoint, ts, pcd,
            result.status, result.duration_ms, result.tax_count,
        ), tags=(result.status,))
        self._update_summary()

    def _update_summary(self):
        p = sum(1 for r in self._results if r.status == "pass")
        f = sum(1 for r in self._results if r.status == "fail")
        e = sum(1 for r in self._results if r.status == "error")
        self._summary.config(text=f"Pass: {p}  Fail: {f}  Error: {e}  Total: {len(self._results)}")

    def _on_select(self, _event=None):
        sel = self._tree.selection()
        if not sel:
            return
        idx = self._tree.index(sel[0])
        if idx >= len(self._results):
            return
        r = self._results[idx]

        for widget, content in [
            (self._req_text, json.dumps(r.test_case.request_body, indent=2, default=str)),
            (self._resp_text, json.dumps(r.response, indent=2, default=str) if r.response else r.error_message),
            (self._assert_text, "\n".join(r.assertion_details) if r.assertion_details else "All assertions passed"),
        ]:
            widget.config(state="normal")
            widget.delete("1.0", "end")
            widget.insert("1.0", content)
            widget.config(state="disabled")

    def _export_csv(self):
        if not self._results:
            return
        path = filedialog.asksaveasfilename(defaultextension=".csv",
                                             filetypes=[("CSV", "*.csv")])
        if not path:
            return
        with open(path, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["id", "endpoint", "status", "duration_ms", "http_status",
                         "tax_count", "error", "assertions"])
            for r in self._results:
                w.writerow([r.test_case.id, r.test_case.endpoint, r.status,
                            r.duration_ms, r.http_status, r.tax_count,
                            r.error_message, "; ".join(r.assertion_details)])
        messagebox.showinfo("Exported", f"CSV saved to {path}")

    def _export_json(self):
        if not self._results:
            return
        path = filedialog.asksaveasfilename(defaultextension=".json",
                                             filetypes=[("JSON", "*.json")])
        if not path:
            return
        data = [r.to_dict() for r in self._results]
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, default=str)
        messagebox.showinfo("Exported", f"JSON saved to {path}")

    def _save_snapshot(self):
        if not self._results:
            return
        path = save_snapshot(self._results)
        messagebox.showinfo("Snapshot", f"Saved to {path}")

    def _compare(self):
        snaps = list_snapshots()
        if len(snaps) < 2:
            messagebox.showinfo("Compare", "Need at least 2 snapshots.")
            return

        win = tk.Toplevel(self)
        win.title("Compare Snapshots")
        win.geometry("600x400")

        ttk.Label(win, text="Snapshot A:").pack(anchor="w", padx=8)
        a_var = tk.StringVar()
        a_combo = ttk.Combobox(win, textvariable=a_var, values=snaps, width=70, state="readonly")
        a_combo.pack(padx=8, pady=4)
        a_combo.current(1)

        ttk.Label(win, text="Snapshot B:").pack(anchor="w", padx=8)
        b_var = tk.StringVar()
        b_combo = ttk.Combobox(win, textvariable=b_var, values=snaps, width=70, state="readonly")
        b_combo.pack(padx=8, pady=4)
        b_combo.current(0)

        result_text = scrolledtext.ScrolledText(win, wrap="word", font=("Consolas", 9))
        result_text.pack(fill="both", expand=True, padx=8, pady=4)

        def _do_compare():
            diffs = diff_snapshots(a_var.get(), b_var.get())
            result_text.delete("1.0", "end")
            if not diffs:
                result_text.insert("1.0", "No differences found.")
            else:
                result_text.insert("1.0", json.dumps(diffs, indent=2, default=str))

        ttk.Button(win, text="Compare", command=_do_compare).pack(pady=8)
