"""
GlassFrog API Client
--------------------
Thin wrapper around the GlassFrog REST API v3.
Only supports authenticated GET requests for now.
"""

from __future__ import annotations

import os
import time
import logging
from typing import Dict, Any, Optional

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


class GlassFrogClient:
    """Simple wrapper to query the GlassFrog API.

    The API is documented at https://glassfrog.com/api.
    Authentication uses an *X-Auth-Token* header.
    """

    BASE_URL = "https://api.glassfrog.com/api/v3"

    def __init__(self, api_key: Optional[str] = None, timeout: int = 15) -> None:
        self.api_key: str = api_key or os.getenv("GLASSFROG_API_KEY", "")
        # Optional: organisation scoping (required for accounts linked to multiple orgs)
        self.org_id: str | None = os.getenv("GLASSFROG_ORG_ID") or None
        if not self.api_key:
            raise ValueError("GLASSFROG_API_KEY missing – cannot initialise GlassFrogClient.")

        self.timeout = timeout
        self.logger = logging.getLogger(self.__class__.__name__)

        # Prepare a requests Session with retries
        self.session = requests.Session()
        retries = Retry(
            total=3,
            backoff_factor=0.5,
            status_forcelist=(429, 500, 502, 503, 504),
            allowed_methods=("GET",),
            raise_on_status=False,
        )
        adapter = HTTPAdapter(max_retries=retries)
        self.session.mount("https://", adapter)
        base_headers = {
            "X-Auth-Token": self.api_key,
            "Accept": "application/json",
            "User-Agent": "Lilly-Dashboard/1.0 (+https://howislilydoing.org)",
        }
        if self.org_id:
            base_headers["X-Organization-Id"] = str(self.org_id)
            self.logger.info("GlassFrogClient: Using org id %s", self.org_id)
        self.session.headers.update(base_headers)

    # ---------------------------------------------------------------------
    # Public helpers
    # ---------------------------------------------------------------------

    def get_role(self, role_id: int) -> Dict[str, Any]:
        """Return role details (projects, metrics). Applies graceful retry if an include list is rejected (422)."""

        include_str = "projects,metrics"  # domains often triggers 422, purpose comes in main payload

        # Try modern endpoint first (no .json suffix)
        endpoints = [
            f"/roles/{role_id}?include={include_str}",
            f"/roles/{role_id}.json?include={include_str}",
            f"/roles/{role_id}",
            f"/roles/{role_id}.json",
        ]

        last_exc: Exception | None = None
        for ep in endpoints:
            try:
                return self._normalise_role(self._get(ep))
            except requests.HTTPError as exc:
                # Save exception and continue to next variant on 404/422 only
                if exc.response is not None and exc.response.status_code in {404, 422}:
                    self.logger.debug("GlassFrog fallback: %s returned %s", ep, exc.response.status_code)
                    last_exc = exc
                    continue
                raise  # re-raise other errors

        # If we exhausted fallbacks, raise the last HTTPError
        if last_exc:
            raise last_exc

        # Should never reach here
        raise RuntimeError("Unable to fetch role from GlassFrog API")

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get(self, endpoint: str) -> Dict[str, Any]:
        url = f"{self.BASE_URL}{endpoint}"
        start = time.perf_counter()
        r = self.session.get(url, timeout=self.timeout)
        duration = (time.perf_counter() - start) * 1000
        self.logger.debug("GET %s – %s in %.0f ms", url, r.status_code, duration)

        # Raise for non-2xx after retry attempts
        r.raise_for_status()
        return r.json()

    # ------------------------------------------------------------------
    # Transformations
    # ------------------------------------------------------------------

    @staticmethod
    def _normalise_role(raw: Dict[str, Any]) -> Dict[str, Any]:
        """Flatten GlassFrog role JSON into a simpler dict."""
        data = raw.get("role", {}) if "role" in raw else raw

        def _list(key: str) -> list:
            return data.get(key, []) or []

        projects = [
            {"id": p.get("id"), "name": p.get("name"), "status": p.get("status")}
            for p in _list("projects")
        ]
        metrics = [
            {
                "id": m.get("id"),
                "name": m.get("name"),
                "value": m.get("target"),  # GlassFrog uses 'target'
                "unit": m.get("unit") or ""
            }
            for m in _list("metrics")
        ]
        accountabilities = _list("accountabilities")

        # Purpose/domain may live in "purpose" or in domains list
        purpose = data.get("purpose")
        if not purpose and _list("domains"):
            purpose = ", ".join(d.get("name", "") for d in data["domains"])

        return {
            "id": data.get("id"),
            "name": data.get("name"),
            "purpose": purpose,
            "accountabilities": accountabilities,
            "projects": projects,
            "metrics": metrics,
        } 