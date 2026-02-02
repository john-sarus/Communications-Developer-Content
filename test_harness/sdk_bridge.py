"""SDK import bridge — adds the auto-generated Python SDK to sys.path and exposes API clients."""

import os
import sys
import logging

log = logging.getLogger(__name__)

_SDK_REL = os.path.join("afc_saaspro_tax", "afc_rest_apis", "SDK", "python")
_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
_SDK_PATH = os.path.join(_REPO_ROOT, _SDK_REL)

ENVIRONMENTS = {
    "UAT": "https://communicationsua.avalara.net",
    "Production": "https://communications.avalara.net",
}


def _ensure_sdk():
    if _SDK_PATH not in sys.path:
        sys.path.insert(0, _SDK_PATH)


class SdkBridge:
    """Lazy wrapper around the auto-generated Python SDK."""

    def __init__(self, username: str, password: str, client_id: str,
                 client_profile_id: str = "", env: str = "UAT"):
        _ensure_sdk()
        import avalara.comms.rest.v2 as sdk
        self._sdk = sdk

        self._env = env
        self._username = username
        self._password = password
        self._client_id = client_id
        self._client_profile_id = client_profile_id

        self._api_client = None

    # ------------------------------------------------------------------
    @property
    def host(self) -> str:
        return ENVIRONMENTS[self._env]

    def _build_client(self):
        if self._api_client is not None:
            return self._api_client
        cfg = self._sdk.Configuration()
        cfg.host = self.host
        cfg.username = self._username
        cfg.password = self._password
        client = self._sdk.ApiClient(configuration=cfg)
        client.default_headers["client_id"] = self._client_id
        if self._client_profile_id:
            client.default_headers["client_profile_id"] = self._client_profile_id
        self._api_client = client
        return client

    def set_env(self, env: str):
        self._env = env
        self._api_client = None  # force rebuild

    def update_credentials(self, username: str, password: str, client_id: str,
                           client_profile_id: str = ""):
        self._username = username
        self._password = password
        self._client_id = client_id
        self._client_profile_id = client_profile_id
        self._api_client = None

    # ------------------------------------------------------------------
    # API facades — each returns an SDK API instance
    # ------------------------------------------------------------------
    def _api(self, cls_name: str):
        client = self._build_client()
        cls = getattr(self._sdk, cls_name)
        return cls(client)

    @property
    def tax_api(self):
        return self._api("JurisdictionDeterminationApi")

    @property
    def sdk(self):
        """Raw SDK module reference."""
        return self._sdk

    # ------------------------------------------------------------------
    # Convenience methods used by the harness
    # ------------------------------------------------------------------
    def health_check(self) -> dict:
        """Call GET /api/v2/afc/serviceInfo to verify connectivity."""
        import urllib.request
        import base64
        import json

        url = f"{self.host}/api/v2/afc/serviceInfo"
        creds = base64.b64encode(f"{self._username}:{self._password}".encode()).decode()
        req = urllib.request.Request(url, headers={
            "Authorization": f"Basic {creds}",
            "client_id": self._client_id,
            "Content-Type": "application/json",
        })
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                return json.loads(resp.read().decode())
        except Exception as exc:
            log.error("Health check failed: %s", exc)
            raise

    def calc_taxes(self, request_body: dict) -> dict:
        """POST /api/v2/afc/calcTaxes with a plain dict body."""
        return self._post("/api/v2/afc/calcTaxes", request_body)

    def commit(self, request_body: dict) -> dict:
        return self._post("/api/v2/afc/commit", request_body)

    def get_ts_pairs(self) -> list:
        return self._get("/api/v2/afc/tsPairs")

    def get_tax_types(self, tax_type: str = "*") -> list:
        return self._get(f"/api/v2/afc/taxType/{tax_type}")

    def pcode_lookup(self, request_body: dict) -> dict:
        return self._post("/api/v2/afc/pCode", request_body)

    def geocode(self, request_body: list) -> list:
        return self._post("/api/v2/geo/geocode", request_body)

    # ------------------------------------------------------------------
    # Low-level HTTP helpers (avoids SDK model-mapping issues)
    # ------------------------------------------------------------------
    def _post(self, path: str, body) -> dict | list:
        import urllib.request
        import base64
        import json

        url = f"{self.host}{path}"
        creds = base64.b64encode(f"{self._username}:{self._password}".encode()).decode()
        data = json.dumps(body).encode()
        req = urllib.request.Request(url, data=data, method="POST", headers={
            "Authorization": f"Basic {creds}",
            "client_id": self._client_id,
            "Content-Type": "application/json",
        })
        if self._client_profile_id:
            req.add_header("client_profile_id", self._client_profile_id)
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode())

    def _get(self, path: str):
        import urllib.request
        import base64
        import json

        url = f"{self.host}{path}"
        creds = base64.b64encode(f"{self._username}:{self._password}".encode()).decode()
        req = urllib.request.Request(url, headers={
            "Authorization": f"Basic {creds}",
            "client_id": self._client_id,
            "Content-Type": "application/json",
        })
        if self._client_profile_id:
            req.add_header("client_profile_id", self._client_profile_id)
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode())
