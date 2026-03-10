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

        ``POST /payments/wallet``
        """
        body = {
            "walletAddress": input.wallet_address,
            "chain": input.chain,
            "signature": input.signature,
            "timestamp": input.timestamp,
        }
        if self._client._sync:
            data = self._client._request_sync("POST", "/payments/wallet", body=body)
        else:
            data = await self._client._request("POST", "/payments/wallet", body=body)
        return Wallet.from_dict(data)

    async def list(self) -> list[Wallet]:
        """List all wallets for the authenticated user.

        ``GET /payments/wallets``
        """
        if self._client._sync:
            data = self._client._request_sync("GET", "/payments/wallets")
        else:
            data = await self._client._request("GET", "/payments/wallets")
        return [Wallet.from_dict(w) for w in data["wallets"]]

    async def remove(self, address: str) -> None:
        """Remove a wallet.

        ``DELETE /payments/wallet/{address}``
        """
        if self._client._sync:
            self._client._request_sync("DELETE", f"/payments/wallet/{address}")
        else:
            await self._client._request("DELETE", f"/payments/wallet/{address}")
