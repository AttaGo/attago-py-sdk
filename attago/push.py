"""Push subscription service for the AttaGo Python SDK."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .types import CreatePushInput, PushSubscriptionResponse

if TYPE_CHECKING:
    from .client import AttaGoClient


class PushService:
    """Manage web push notification subscriptions."""

    def __init__(self, client: AttaGoClient) -> None:
        self._client = client

    async def list(self) -> list[PushSubscriptionResponse]:
        """List all push subscriptions for the authenticated user.

        ``GET /push/subscriptions``
        """
        if self._client._sync:
            data = self._client._request_sync("GET", "/user/push-subscriptions")
        else:
            data = await self._client._request("GET", "/user/push-subscriptions")
        return [PushSubscriptionResponse.from_dict(s) for s in data["subscriptions"]]

    async def create(self, input: CreatePushInput) -> PushSubscriptionResponse:
        """Register a push subscription.

        ``POST /push/subscriptions``
        """
        body = {
            "endpoint": input.endpoint,
            "keys": {
                "p256dh": input.keys.p256dh,
                "auth": input.keys.auth,
            },
        }
        if self._client._sync:
            data = self._client._request_sync("POST", "/user/push-subscriptions", body=body)
        else:
            data = await self._client._request("POST", "/user/push-subscriptions", body=body)
        return PushSubscriptionResponse.from_dict(data)

    async def delete(self, subscription_id: str) -> None:
        """Delete a push subscription.

        ``DELETE /push/subscriptions/{subscription_id}``
        """
        if self._client._sync:
            self._client._request_sync("DELETE", f"/user/push-subscriptions/{subscription_id}")
        else:
            await self._client._request("DELETE", f"/user/push-subscriptions/{subscription_id}")
