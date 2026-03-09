"""Data service -- latest snapshots, per-token data, and data-push retrieval.

Wraps the ``/v1/data/latest``, ``/v1/api/data/{token}``, and
``/v1/data/push/{requestId}`` endpoints.
"""

from __future__ import annotations

from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from .client import AttaGoClient

from .types import DataLatestResponse, DataTokenResponse, DataPushResponse


class DataService:
    """Data endpoints -- latest snapshots, per-token data, and data pushes.

    Async usage::

        latest = await client.data.get_latest()
        btc = await client.data.get_token_data("BTC")

    Sync usage::

        latest = client.data.get_latest_sync()
        btc = client.data.get_token_data_sync("BTC")
    """

    def __init__(self, client: AttaGoClient) -> None:
        self._client = client

    # ── Latest ───────────────────────────────────────────────────────

    async def get_latest(self) -> DataLatestResponse:
        """Get latest snapshot of all assets.

        ``GET /v1/data/latest``
        """
        data = await self._client._request("GET", "/data/latest")
        return DataLatestResponse.from_dict(data)

    def get_latest_sync(self) -> DataLatestResponse:
        """Synchronous version of :meth:`get_latest`."""
        data = self._client._request_sync("GET", "/data/latest")
        return DataLatestResponse.from_dict(data)

    # ── Token data ───────────────────────────────────────────────────

    async def get_token_data(self, token: str) -> DataTokenResponse:
        """Get full data for a single token (auth-gated, consumes a push).

        ``GET /v1/api/data/{token}``
        """
        data = await self._client._request("GET", f"/api/data/{token}")
        return DataTokenResponse.from_dict(data)

    def get_token_data_sync(self, token: str) -> DataTokenResponse:
        """Synchronous version of :meth:`get_token_data`."""
        data = self._client._request_sync("GET", f"/api/data/{token}")
        return DataTokenResponse.from_dict(data)

    # ── Data push ────────────────────────────────────────────────────

    async def get_data_push(self, request_id: str) -> DataPushResponse:
        """Retrieve a previously-created data push by request ID.

        ``GET /v1/data/push/{requestId}``
        """
        data = await self._client._request("GET", f"/data/push/{request_id}")
        return DataPushResponse.from_dict(data)

    def get_data_push_sync(self, request_id: str) -> DataPushResponse:
        """Synchronous version of :meth:`get_data_push`."""
        data = self._client._request_sync("GET", f"/data/push/{request_id}")
        return DataPushResponse.from_dict(data)
