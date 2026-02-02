"""Tab 1: Credentials, environment selector, health check."""

from __future__ import annotations
import threading
import tkinter as tk
from tkinter import ttk, messagebox

from .. import config


class ConfigPanel(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self._build()
        self._load_stored()

    def _build(self):
        pad = dict(padx=8, pady=4)

        # Credentials
        cred_frame = ttk.LabelFrame(self, text="Credentials")
        cred_frame.pack(fill="x", **pad)

        labels = ["Username", "Password", "Client ID", "Client Profile ID"]
        self._entries: dict[str, tk.Entry] = {}
        for i, lbl in enumerate(labels):
            ttk.Label(cred_frame, text=lbl + ":").grid(row=i, column=0, sticky="e", **pad)
            var = tk.StringVar()
            show = "*" if lbl == "Password" else ""
            ent = ttk.Entry(cred_frame, textvariable=var, width=40, show=show)
            ent.grid(row=i, column=1, sticky="w", **pad)
            key = lbl.lower().replace(" ", "_")
            self._entries[key] = ent
            self._entries[key + "_var"] = var

        # Show/hide password
        self._pw_visible = False
        ttk.Button(cred_frame, text="Show", width=6,
                   command=self._toggle_pw).grid(row=1, column=2, **pad)

        # Save / Delete
        btn_frame = ttk.Frame(cred_frame)
        btn_frame.grid(row=len(labels), column=0, columnspan=3, **pad)
        ttk.Button(btn_frame, text="Save Credentials", command=self._save).pack(side="left", padx=4)
        ttk.Button(btn_frame, text="Delete Credentials", command=self._delete).pack(side="left", padx=4)

        # Environment
        env_frame = ttk.LabelFrame(self, text="Environment")
        env_frame.pack(fill="x", **pad)
        self._env_var = tk.StringVar(value="UAT")
        for val in ("UAT", "Production"):
            ttk.Radiobutton(env_frame, text=val, variable=self._env_var,
                            value=val).pack(side="left", **pad)

        # Health check
        hc_frame = ttk.Frame(self)
        hc_frame.pack(fill="x", **pad)
        ttk.Button(hc_frame, text="Test Connection", command=self._test_connection).pack(side="left")
        self._hc_label = ttk.Label(hc_frame, text="")
        self._hc_label.pack(side="left", padx=12)

    def _toggle_pw(self):
        self._pw_visible = not self._pw_visible
        self._entries["password"].config(show="" if self._pw_visible else "*")

    def _load_stored(self):
        creds = config.get_credentials()
        if creds:
            for key in ("username", "password", "client_id", "client_profile_id"):
                self._entries[key + "_var"].set(creds.get(key, ""))

    def _save(self):
        config.store_credentials(
            self._entries["username_var"].get(),
            self._entries["password_var"].get(),
            self._entries["client_id_var"].get(),
            self._entries["client_profile_id_var"].get(),
        )
        self.app.refresh_bridge(
            self._entries["username_var"].get(),
            self._entries["password_var"].get(),
            self._entries["client_id_var"].get(),
            self._entries["client_profile_id_var"].get(),
            self._env_var.get(),
        )
        messagebox.showinfo("Saved", "Credentials saved to keyring.")

    def _delete(self):
        config.delete_credentials()
        for key in ("username", "password", "client_id", "client_profile_id"):
            self._entries[key + "_var"].set("")
        messagebox.showinfo("Deleted", "Credentials removed from keyring.")

    def _test_connection(self):
        self._hc_label.config(text="Connecting...", foreground="gray")

        def _check():
            try:
                self.app.refresh_bridge(
                    self._entries["username_var"].get(),
                    self._entries["password_var"].get(),
                    self._entries["client_id_var"].get(),
                    self._entries["client_profile_id_var"].get(),
                    self._env_var.get(),
                )
                info = self.app.bridge.health_check()
                msg = f"Connected — {info}"
                self.after(0, lambda: self._hc_label.config(text=msg, foreground="green"))
                self.after(0, lambda: self.app.set_status(f"Connected to {self._env_var.get()}"))
            except Exception as exc:
                self.after(0, lambda: self._hc_label.config(
                    text=f"Failed: {exc}", foreground="red"))

        threading.Thread(target=_check, daemon=True).start()

    @property
    def env(self) -> str:
        return self._env_var.get()
