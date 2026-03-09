"""Tests for attago.agent -- AgentService."""

from __future__ import annotations

import json

import httpx
import pytest

from attago.agent import AgentService
from attago.client import AttaGoClient


# ── Fixtures ────────────────────────────────────────────────────────

SCORE_JSON = {
    "token": "BTC",
    "composite": {
        "score": 72.5,
        "signal": "GO",
        "confidence": 0.85,
    },
    "spot": {"price": 62000, "change24h": 2.1},
    "perps": {"fundingRate": 0.01},
    "context": {"dominance": 52.3},
    "market": {"totalCap": "2.1T"},
    "derivSymbols": ["BTCUSDT"],
    "hasDerivatives": True,
    "sources": [{"name": "coinglass", "status": "ok"}],
    "meta": {"schemaVersion": "4.0"},
    "requestId": "req_abc123",
}

DATA_JSON = {
    "assets": {
        "BTC": {"price": 62000},
        "ETH": {"price": 3400},
    },
    "assetOrder": ["BTC", "ETH"],
    "market": {"totalCap": "2.1T"},
    "sources": [{"name": "coinglass", "status": "ok"}],
    "meta": {"schemaVersion": "4.0"},
    "requestId": "req_data456",
}


# ── Async tests ─────────────────────────────────────────────────────


class TestAgentServiceAsync:
    @pytest.mark.asyncio
    async def test_get_score(self) -> None:
        """get_score returns a hydrated AgentScoreResponse."""

        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json=SCORE_JSON)

        async with AttaGoClient(
            api_key="ak_test",
            base_url="https://api.test.com",
            transport=httpx.MockTransport(handler),
        ) as client:
            svc = AgentService(client)
            result = await svc.get_score("BTC")

        assert result.token == "BTC"
        assert result.composite.score == 72.5
        assert result.composite.signal == "GO"
        assert result.composite.confidence == 0.85
        assert result.has_derivatives is True
        assert result.deriv_symbols == ["BTCUSDT"]
        assert result.request_id == "req_abc123"

    @pytest.mark.asyncio
    async def test_get_score_sends_symbol_param(self) -> None:
        """get_score sends the symbol as a query parameter."""
        captured_url = None

        def handler(request: httpx.Request) -> httpx.Response:
            nonlocal captured_url
            captured_url = str(request.url)
            return httpx.Response(200, json=SCORE_JSON)

        async with AttaGoClient(
            api_key="ak_test",
            base_url="https://api.test.com",
            transport=httpx.MockTransport(handler),
        ) as client:
            svc = AgentService(client)
            await svc.get_score("ETH")

        assert captured_url is not None
        assert "symbol=ETH" in captured_url
        assert "/v1/agent/score" in captured_url

    @pytest.mark.asyncio
    async def test_get_data(self) -> None:
        """get_data returns a hydrated AgentDataResponse."""

        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json=DATA_JSON)

        async with AttaGoClient(
            api_key="ak_test",
            base_url="https://api.test.com",
            transport=httpx.MockTransport(handler),
        ) as client:
            svc = AgentService(client)
            result = await svc.get_data("BTC", "ETH")

        assert "BTC" in result.assets
        assert "ETH" in result.assets
        assert result.asset_order == ["BTC", "ETH"]
        assert result.request_id == "req_data456"

    @pytest.mark.asyncio
    async def test_get_data_sends_symbols_param(self) -> None:
        """get_data joins multiple symbols with commas in the query string."""
        captured_url = None

        def handler(request: httpx.Request) -> httpx.Response:
            nonlocal captured_url
            captured_url = str(request.url)
            return httpx.Response(200, json=DATA_JSON)

        async with AttaGoClient(
            api_key="ak_test",
            base_url="https://api.test.com",
            transport=httpx.MockTransport(handler),
        ) as client:
            svc = AgentService(client)
            await svc.get_data("BTC", "ETH")

        assert captured_url is not None
        assert "symbols=BTC%2CETH" in captured_url or "symbols=BTC,ETH" in captured_url
        assert "/v1/agent/data" in captured_url

    @pytest.mark.asyncio
    async def test_get_data_no_symbols(self) -> None:
        """get_data with no args omits the symbols param entirely."""
        captured_url = None

        def handler(request: httpx.Request) -> httpx.Response:
            nonlocal captured_url
            captured_url = str(request.url)
            return httpx.Response(200, json=DATA_JSON)

        async with AttaGoClient(
            api_key="ak_test",
            base_url="https://api.test.com",
            transport=httpx.MockTransport(handler),
        ) as client:
            svc = AgentService(client)
            await svc.get_data()

        assert captured_url is not None
        assert "symbols" not in captured_url


# ── Sync tests ──────────────────────────────────────────────────────


class TestAgentServiceSync:
    def test_get_score_sync(self) -> None:
        """get_score_sync returns a hydrated AgentScoreResponse."""

        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json=SCORE_JSON)

        client = AttaGoClient(
            api_key="ak_test",
            base_url="https://api.test.com",
            sync=True,
            sync_transport=httpx.MockTransport(handler),
        )
        with client:
            svc = AgentService(client)
            result = svc.get_score_sync("BTC")

        assert result.token == "BTC"
        assert result.composite.signal == "GO"
        assert result.request_id == "req_abc123"

    def test_get_data_sync(self) -> None:
        """get_data_sync returns a hydrated AgentDataResponse."""

        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json=DATA_JSON)

        client = AttaGoClient(
            api_key="ak_test",
            base_url="https://api.test.com",
            sync=True,
            sync_transport=httpx.MockTransport(handler),
        )
        with client:
            svc = AgentService(client)
            result = svc.get_data_sync("BTC", "ETH")

        assert "BTC" in result.assets
        assert result.asset_order == ["BTC", "ETH"]
