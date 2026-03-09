"""Payment service for the AttaGo Python SDK."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .types import BillingStatus, SubscribeInput, SubscribeResponse, UpgradeQuote

if TYPE_CHECKING:
    from .client import AttaGoClient


class PaymentService:
    """Subscribe, check billing status, and get upgrade quotes."""

    def __init__(self, client: AttaGoClient) -> None:
        self._client = client

    async def subscribe(self, input: SubscribeInput) -> SubscribeResponse:
        """Subscribe to a billing tier.

        ``POST /payments/subscribe``
        """
        body = {
            "tier": input.tier,
            "billingCycle": input.billing_cycle,
            "renew": input.renew,
        }
        if self._client._sync:
            data = self._client._request_sync("POST", "/payments/subscribe", body=body)
        else:
            data = await self._client._request("POST", "/payments/subscribe", body=body)
        return SubscribeResponse.from_dict(data)

    async def status(self) -> BillingStatus:
        """Get the current billing/tier status.

        ``GET /payments/status``
        """
        if self._client._sync:
            data = self._client._request_sync("GET", "/payments/status")
        else:
            data = await self._client._request("GET", "/payments/status")
        return BillingStatus.from_dict(data)

    async def upgrade_quote(self, tier: str, cycle: str) -> UpgradeQuote:
        """Get a pro-rated upgrade price quote.

        ``GET /payments/upgrade-quote?tier=X&cycle=Y``
        """
        if self._client._sync:
            data = self._client._request_sync(
                "GET", "/payments/upgrade-quote", params={"tier": tier, "cycle": cycle}
            )
        else:
            data = await self._client._request(
                "GET", "/payments/upgrade-quote", params={"tier": tier, "cycle": cycle}
            )
        return UpgradeQuote.from_dict(data)
