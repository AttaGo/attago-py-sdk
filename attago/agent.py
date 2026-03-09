"""Agent service -- Go/No-Go scores and full market data.

Wraps the ``/v1/agent/score`` and ``/v1/agent/data`` endpoints.
"""

from __future__ import annotations

from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from .client import AttaGoClient

from .types import AgentScoreResponse, AgentDataResponse


class AgentService:
    """Agent endpoints -- Go/No-Go scores and full market data.

    Async usage::

        score = await client.agent.get_score("BTC")
        print(score.composite.signal)  # "GO", "NO-GO", "NEUTRAL"

    Sync usage::

        score = client.agent.get_score_sync("BTC")
    """

    def __init__(self, client: AttaGoClient) -> None:
        self._client = client

    # ── Score ────────────────────────────────────────────────────────

    async def get_score(self, symbol: str) -> AgentScoreResponse:
        """Get Go/No-Go score for a single token.

        ``GET /v1/agent/score?symbol={symbol}``
        """
        data = await self._client._request(
            "GET", "/agent/score", params={"symbol": symbol},
        )
        return AgentScoreResponse.from_dict(data)

    def get_score_sync(self, symbol: str) -> AgentScoreResponse:
        """Synchronous version of :meth:`get_score`."""
        data = self._client._request_sync(
            "GET", "/agent/score", params={"symbol": symbol},
        )
        return AgentScoreResponse.from_dict(data)

    # ── Data ─────────────────────────────────────────────────────────

    async def get_data(self, *symbols: str) -> AgentDataResponse:
        """Get full market data for one or more tokens.

        ``GET /v1/agent/data?symbols={comma-separated}``

        When called with no arguments, returns data for all tokens.
        """
        params: dict[str, str] = {}
        if symbols:
            params["symbols"] = ",".join(symbols)
        data = await self._client._request("GET", "/agent/data", params=params)
        return AgentDataResponse.from_dict(data)

    def get_data_sync(self, *symbols: str) -> AgentDataResponse:
        """Synchronous version of :meth:`get_data`."""
        params: dict[str, str] = {}
        if symbols:
            params["symbols"] = ",".join(symbols)
        data = self._client._request_sync("GET", "/agent/data", params=params)
        return AgentDataResponse.from_dict(data)
