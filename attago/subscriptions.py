"""Subscription management service for the AttaGo Python SDK."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .types import CatalogResponse, CreateSubscriptionInput, Subscription, UpdateSubscriptionInput

if TYPE_CHECKING:
    from .client import AttaGoClient


class SubscriptionService:
    """CRUD operations for alert subscriptions."""

    def __init__(self, client: AttaGoClient) -> None:
        self._client = client

    async def catalog(self) -> CatalogResponse:
        """Fetch the subscription catalog (available tokens, metrics, limits).

        ``GET /subscriptions/catalog``
        """
        if self._client._sync:
            data = self._client._request_sync("GET", "/subscriptions/catalog")
        else:
            data = await self._client._request("GET", "/subscriptions/catalog")
        return CatalogResponse.from_dict(data)

    async def list(self) -> list[Subscription]:
        """List all subscriptions for the authenticated user.

        ``GET /subscriptions``
        """
        if self._client._sync:
            data = self._client._request_sync("GET", "/user/subscriptions")
        else:
            data = await self._client._request("GET", "/user/subscriptions")
        return [Subscription.from_dict(s) for s in data["subscriptions"]]

    async def create(self, input: CreateSubscriptionInput) -> Subscription:
        """Create a new alert subscription.

        ``POST /subscriptions``
        """
        body: dict = {
            "tokenId": input.token_id,
            "label": input.label,
            "groups": [
                [
                    {
                        "metricName": c.metric_name,
                        "thresholdOp": c.threshold_op,
                        "thresholdVal": c.threshold_val,
                    }
                    for c in group
                ]
                for group in input.groups
            ],
        }
        if input.cooldown_minutes is not None:
            body["cooldownMinutes"] = input.cooldown_minutes
        if self._client._sync:
            data = self._client._request_sync("POST", "/user/subscriptions", body=body)
        else:
            data = await self._client._request("POST", "/user/subscriptions", body=body)
        return Subscription.from_dict(data)

    async def update(self, sub_id: str, input: UpdateSubscriptionInput) -> Subscription:
        """Update an existing subscription.

        ``PUT /subscriptions/{sub_id}``
        """
        body: dict = {}
        if input.label is not None:
            body["label"] = input.label
        if input.groups is not None:
            body["groups"] = [
                [
                    {
                        "metricName": c.metric_name,
                        "thresholdOp": c.threshold_op,
                        "thresholdVal": c.threshold_val,
                    }
                    for c in group
                ]
                for group in input.groups
            ]
        if input.cooldown_minutes is not None:
            body["cooldownMinutes"] = input.cooldown_minutes
        if input.is_active is not None:
            body["isActive"] = input.is_active
        if self._client._sync:
            data = self._client._request_sync("PUT", f"/user/subscriptions/{sub_id}", body=body)
        else:
            data = await self._client._request("PUT", f"/user/subscriptions/{sub_id}", body=body)
        return Subscription.from_dict(data)

    async def delete(self, sub_id: str) -> None:
        """Delete a subscription.

        ``DELETE /subscriptions/{sub_id}``
        """
        if self._client._sync:
            self._client._request_sync("DELETE", f"/user/subscriptions/{sub_id}")
        else:
            await self._client._request("DELETE", f"/user/subscriptions/{sub_id}")
