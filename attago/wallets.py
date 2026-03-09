"""Wallet management service for the AttaGo Python SDK."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .types import RegisterWalletInput, Wallet

if TYPE_CHECKING:
    from .client import AttaGoClient


class WalletService:
    """Register, list, and remove verified wallets."""

    def __init__(self, client: AttaGoClient) -> None:
        self._client = client

    async def register(self, input: RegisterWalletInput) -> Wallet:
        """Register a new wallet.

        ``POST /wallets``
        """
        body = {
            "walletAddress": input.wallet_address,
            "chain": input.chain,
            "signature": input.signature,
            "timestamp": input.timestamp,
        }
        if self._client._sync:
            data = self._client._request_sync("POST", "/wallets", body=body)
        else:
            data = await self._client._request("POST", "/wallets", body=body)
        return Wallet.from_dict(data)

    async def list(self) -> list[Wallet]:
        """List all wallets for the authenticated user.

        ``GET /wallets``
        """
        if self._client._sync:
            data = self._client._request_sync("GET", "/wallets")
        else:
            data = await self._client._request("GET", "/wallets")
        return [Wallet.from_dict(w) for w in data["wallets"]]

    async def remove(self, address: str) -> None:
        """Remove a wallet.

        ``DELETE /wallets/{address}``
        """
        if self._client._sync:
            self._client._request_sync("DELETE", f"/wallets/{address}")
        else:
            await self._client._request("DELETE", f"/wallets/{address}")
