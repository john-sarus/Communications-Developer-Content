"""Tab 4: Execution progress, live log, stop button."""

from __future__ import annotations
import logging
import tkinter as tk
from tkinter import ttk, scrolledtext


class _TextHandler(logging.Handler):
    """Logging handler that appends to a ScrolledText widget."""

    def __init__(self, widget: scrolledtext.ScrolledText):
        super().__init__()
        self._widget = widget

    def emit(self, record):
        msg = self.format(record) + "\n"
        try:
            self._widget.after(0, self._append, msg)
        except Exception:
            pass

    def _append(self, msg):
        self._widget.config(state="normal")
        self._widget.insert("end", msg)
        self._widget.see("end")
        self._widget.config(state="disabled")


class ExecutionPanel(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self._build()
        self._setup_logging()

    def _build(self):
        pad = dict(padx=6, pady=3)

        top = ttk.Frame(self)
        top.pack(fill="x", **pad)

        self._progress = ttk.Progressbar(top, mode="determinate", length=400)
        self._progress.pack(side="left", fill="x", expand=True, **pad)

        self._count_label = ttk.Label(top, text="0 / 0")
        self._count_label.pack(side="left", **pad)

        self._stop_btn = ttk.Button(top, text="Stop", command=self._stop, state="disabled")
        self._stop_btn.pack(side="right", **pad)

        self._log = scrolledtext.ScrolledText(self, wrap="word", state="disabled",
                                               height=25, font=("Consolas", 9))
        self._log.pack(fill="both", expand=True, **pad)

    def _setup_logging(self):
        handler = _TextHandler(self._log)
        handler.setLevel(logging.INFO)
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s",
                                                datefmt="%H:%M:%S"))
        logging.getLogger("test_harness").addHandler(handler)

    def on_start(self, total: int):
        self._progress["maximum"] = total
        self._progress["value"] = 0
        self._count_label.config(text=f"0 / {total}")
        self._stop_btn.config(state="normal")
        self._clear_log()

    def on_progress(self, current: int, total: int):
        self._progress["value"] = current
        self._count_label.config(text=f"{current} / {total}")

    def on_done(self):
        self._progress["value"] = self._progress["maximum"]
        self._stop_btn.config(state="disabled")

    def _stop(self):
        self.app.stop_tests()

    def _clear_log(self):
        self._log.config(state="normal")
        self._log.delete("1.0", "end")
        self._log.config(state="disabled")
