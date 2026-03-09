"""Bundle management service for the AttaGo Python SDK."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .types import BundleListResponse, BundlePurchaseResponse, PurchaseBundleInput

if TYPE_CHECKING:
    from .client import AttaGoClient


class BundleService:
    """List available bundles and purchase data-push credits."""

    def __init__(self, client: AttaGoClient) -> None:
        self._client = client

    async def list(self) -> BundleListResponse:
        """List purchased bundles and the bundle catalog.

        ``GET /bundles``
        """
        if self._client._sync:
            data = self._client._request_sync("GET", "/bundles")
        else:
            data = await self._client._request("GET", "/bundles")
        return BundleListResponse.from_dict(data)

    async def purchase(self, input: PurchaseBundleInput) -> BundlePurchaseResponse:
        """Purchase a data-push credit bundle.

        ``POST /bundles``
        """
        body = {
            "bundleIndex": input.bundle_index,
            "walletAddress": input.wallet_address,
        }
        if self._client._sync:
            data = self._client._request_sync("POST", "/bundles", body=body)
        else:
            data = await self._client._request("POST", "/bundles", body=body)
        return BundlePurchaseResponse.from_dict(data)
