"""GlassFrogService
--------------------
Provides cached access to GlassFrog role information.

This acts as a thin wrapper around `tools.glassfrog_client.GlassFrogClient`
so that the rest of the Flask app can remain unaware of HTTP / auth details.
"""

from __future__ import annotations

import logging
from typing import Dict, Any

from flask_caching import Cache

from tools.glassfrog_client import GlassFrogClient


class GlassFrogService:
    """Business-level helper to fetch & cache GlassFrog role data."""

    CACHE_KEY_TEMPLATE = "glassfrog.role.{role_id}"

    def __init__(self, client: GlassFrogClient, cache: Cache, ttl_seconds: int = 600) -> None:
        self.client = client
        self.cache = cache
        self.ttl = ttl_seconds
        self.logger = logging.getLogger(self.__class__.__name__)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_role(self, role_id: int, force_refresh: bool = False) -> Dict[str, Any]:
        cache_key = self.CACHE_KEY_TEMPLATE.format(role_id=role_id)

        if not force_refresh:
            cached: Dict[str, Any] | None = self.cache.get(cache_key)
            if cached:
                self.logger.debug("Cache hit for role %s", role_id)
                return cached

        # Either force_refresh or cache miss
        self.logger.debug("Cache miss – fetching role %s from GlassFrog API", role_id)
        try:
            data = self.client.get_role(role_id)
        except Exception as exc:
            self.logger.error("GlassFrog API error: %s", exc, exc_info=True)
            raise

        # Store in cache
        self.cache.set(cache_key, data, timeout=self.ttl)
        return data 