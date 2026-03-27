"""Messaging service -- list, link/unlink Telegram, and test delivery."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .client import AttaGoClient

from .types import (
    MessagingLink,
    MessagingLinkResult,
    MessagingTestResult,
)


class MessagingService:
    """Manage messaging channel links (Telegram, etc.)."""

    def __init__(self, client: AttaGoClient) -> None:
        self._client = client

    async def list(self) -> list[MessagingLink]:
        """List all linked messaging channels.

        ``GET /user/messaging``
        """
        if self._client._sync:
            data = self._client._request_sync("GET", "/user/messaging")
        else:
            data = await self._client._request("GET", "/user/messaging")
        return [MessagingLink.from_dict(m) for m in data.get("channels", [])]

    async def link_telegram(self, code: str) -> MessagingLinkResult:
        """Link a Telegram account using a verification code.

        ``POST /user/messaging/telegram/link``
        """
        if self._client._sync:
            data = self._client._request_sync(
                "POST", "/user/messaging/telegram/link", body={"code": code}
            )
        else:
            data = await self._client._request(
                "POST", "/user/messaging/telegram/link", body={"code": code}
            )
        return MessagingLinkResult.from_dict(data)

    async def unlink_telegram(self) -> dict[str, bool]:
        """Unlink the Telegram account.

        ``DELETE /user/messaging/telegram``
        """
        if self._client._sync:
            data = self._client._request_sync("DELETE", "/user/messaging/telegram")
        else:
            data = await self._client._request("DELETE", "/user/messaging/telegram")
        return {"unlinked": data.get("unlinked", True)}

    async def test(self) -> MessagingTestResult:
        """Send a test message to all linked messaging channels.

        ``POST /user/messaging/test``
        """
        if self._client._sync:
            data = self._client._request_sync("POST", "/user/messaging/test")
        else:
            data = await self._client._request("POST", "/user/messaging/test")
        return MessagingTestResult.from_dict(data)
