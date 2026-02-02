"""Main application: Tk root, notebook tabs, orchestration."""

from __future__ import annotations
import logging
import os
import threading
import tkinter as tk
from tkinter import ttk

from .config import get_credentials
from .sdk_bridge import SdkBridge
from .core.test_runner import TestRunner
from .models.test_case import TestCase

from .ui.config_panel import ConfigPanel
from .ui.test_builder import TestBuilder
from .ui.sample_browser import SampleBrowser
from .ui.execution_panel import ExecutionPanel
from .ui.results_panel import ResultsPanel

log = logging.getLogger("test_harness")


class App:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("AvaTax Comms REST v2 Test Harness")
        self.root.geometry("1200x800")

        self.bridge: SdkBridge | None = None
        self.base_template: dict | None = None
        self._runner: TestRunner | None = None

        self._setup_logging()
        self._build_ui()
        self._try_auto_connect()

    # ------------------------------------------------------------------
    def _setup_logging(self):
        os.makedirs(os.path.join(os.path.dirname(__file__), "logs"), exist_ok=True)
        from datetime import date
        fh = logging.FileHandler(
            os.path.join(os.path.dirname(__file__), "logs", f"harness_{date.today()}.log"),
            encoding="utf-8",
        )
        fh.setLevel(logging.DEBUG)
        fh.setFormatter(logging.Formatter("%(asctime)s %(name)s %(levelname)s %(message)s"))
        logging.getLogger("test_harness").addHandler(fh)
        logging.getLogger("test_harness").setLevel(logging.DEBUG)

    def _build_ui(self):
        self._nb = ttk.Notebook(self.root)
        self._nb.pack(fill="both", expand=True)

        self.config_panel = ConfigPanel(self._nb, self)
        self._nb.add(self.config_panel, text="Configuration")

        self.test_builder = TestBuilder(self._nb, self)
        self._nb.add(self.test_builder, text="Test Builder")

        self.sample_browser = SampleBrowser(self._nb, self)
        self._nb.add(self.sample_browser, text="Sample Browser")

        self.exec_panel = ExecutionPanel(self._nb, self)
        self._nb.add(self.exec_panel, text="Execution")

        self.results_panel = ResultsPanel(self._nb, self)
        self._nb.add(self.results_panel, text="Results")

        # Status bar
        self._status = ttk.Label(self.root, text="Not connected", relief="sunken", anchor="w")
        self._status.pack(fill="x", side="bottom")

    def _try_auto_connect(self):
        creds = get_credentials()
        if creds:
            self.refresh_bridge(
                creds["username"], creds["password"],
                creds["client_id"], creds.get("client_profile_id", ""),
            )
            self._bg_startup()
        else:
            self._nb.select(0)  # Focus config tab

    def refresh_bridge(self, username, password, client_id, client_profile_id="", env="UAT"):
        if self.bridge:
            self.bridge.update_credentials(username, password, client_id, client_profile_id)
            self.bridge.set_env(env)
        else:
            self.bridge = SdkBridge(username, password, client_id, client_profile_id, env)

    def _bg_startup(self):
        """Background: health check + fetch TS pairs."""
        def _work():
            try:
                info = self.bridge.health_check()
                self.root.after(0, lambda: self.set_status(
                    f"Connected to {self.bridge._env} — {info}"))
            except Exception as exc:
                self.root.after(0, lambda: self.set_status(f"Connection failed: {exc}"))
                return

            try:
                pairs = self.bridge.get_ts_pairs()
                self.root.after(0, lambda: self.test_builder.populate_ts_pairs(pairs))
                log.info("Loaded %d TS pairs", len(pairs))
            except Exception as exc:
                log.warning("Failed to load TS pairs: %s", exc)

        threading.Thread(target=_work, daemon=True).start()

    def set_status(self, text: str):
        self._status.config(text=text)

    # ------------------------------------------------------------------
    # Test execution
    # ------------------------------------------------------------------
    def run_tests(self, cases: list[TestCase]):
        if not self.bridge:
            self.set_status("No connection — configure credentials first")
            self._nb.select(0)
            return

        self.results_panel.clear()
        self.exec_panel.on_start(len(cases))
        self._nb.select(self.exec_panel)
        log.info("Starting run: %d test cases", len(cases))

        self._runner = TestRunner(
            bridge=self.bridge,
            on_progress=self.exec_panel.on_progress,
            on_result=self._on_result,
            on_done=self._on_done,
            root=self.root,
        )
        self._runner.start(cases)

    def stop_tests(self):
        if self._runner:
            self._runner.stop()
            log.info("Run stopped by user")

    def _on_result(self, result):
        self.results_panel.add_result(result)
        status = result.status.upper()
        log.info("[%s] %s — %s (%.0fms, %d taxes)",
                 status, result.test_case.endpoint, result.test_case.description,
                 result.duration_ms, result.tax_count)

    def _on_done(self):
        self.exec_panel.on_done()
        total = len(self.results_panel._results)
        passed = sum(1 for r in self.results_panel._results if r.status == "pass")
        self.set_status(f"Run complete: {passed}/{total} passed")
        log.info("Run complete: %d/%d passed", passed, total)
        self._nb.select(self.results_panel)

    # ------------------------------------------------------------------
    def run(self):
        self.root.mainloop()
