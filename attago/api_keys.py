"""API key management service for the AttaGo Python SDK."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .types import ApiKeyCreateResponse, ApiKeyListItem

if TYPE_CHECKING:
    from .client import AttaGoClient


class ApiKeyService:
    """Create, list, and revoke API keys."""

    def __init__(self, client: AttaGoClient) -> None:
        self._client = client

    async def create(self, name: str) -> ApiKeyCreateResponse:
        """Create a new API key.

        ``POST /api-keys``
        """
        body = {"name": name}
        if self._client._sync:
            data = self._client._request_sync("POST", "/user/api-keys", body=body)
        else:
            data = await self._client._request("POST", "/user/api-keys", body=body)
        return ApiKeyCreateResponse.from_dict(data)

    async def list(self) -> list[ApiKeyListItem]:
        """List all API keys for the authenticated user.

        ``GET /api-keys``
        """
        if self._client._sync:
            data = self._client._request_sync("GET", "/user/api-keys")
        else:
            data = await self._client._request("GET", "/user/api-keys")
        return [ApiKeyListItem.from_dict(k) for k in data["keys"]]

    async def revoke(self, key_id: str) -> None:
        """Revoke an API key.

        ``DELETE /api-keys/{key_id}``
        """
        if self._client._sync:
            self._client._request_sync("DELETE", f"/user/api-keys/{key_id}")
        else:
            await self._client._request("DELETE", f"/user/api-keys/{key_id}")
