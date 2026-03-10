"""Redemption code service for the AttaGo Python SDK."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .types import RedeemResponse

if TYPE_CHECKING:
    from .client import AttaGoClient


class RedeemService:
    """Redeem promotional or subscription codes."""

    def __init__(self, client: AttaGoClient) -> None:
        self._client = client

    async def redeem(self, code: str) -> RedeemResponse:
        """Redeem a code.

        ``POST /redeem``
        """
        body = {"code": code}
        if self._client._sync:
            data = self._client._request_sync("POST", "/user/redeem", body=body)
        else:
            data = await self._client._request("POST", "/user/redeem", body=body)
        return RedeemResponse.from_dict(data)
