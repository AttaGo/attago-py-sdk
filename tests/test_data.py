"""Tests for attago.data -- DataService."""

from __future__ import annotations

import httpx
import pytest

from attago.data import DataService
from attago.client import AttaGoClient


# ── Fixtures ────────────────────────────────────────────────────────

LATEST_JSON = {
    "assets": {
        "BTC": {"price": 62000, "change24h": 2.1},
        "ETH": {"price": 3400, "change24h": -0.5},
    },
    "assetOrder": ["BTC", "ETH"],
    "market": {"totalCap": "2.1T"},
    "sources": [{"name": "coinglass", "status": "ok"}],
    "meta": {"schemaVersion": "4.0"},
}

TOKEN_DATA_JSON = {
    "token": "BTC",
    "composite": {"score": 72.5, "signal": "GO", "confidence": 0.85},
    "spot": {"price": 62000},
    "perps": {"fundingRate": 0.01},
    "context": {"dominance": 52.3},
    "market": {"totalCap": "2.1T"},
    "derivSymbols": ["BTCUSDT"],
    "hasDerivatives": True,
    "sources": [{"name": "coinglass", "status": "ok"}],
    "meta": {"schemaVersion": "4.0"},
    "requestId": "req_tok789",
    "mode": "testnet",
    "bundle": {"bundleId": "bun_001", "remaining": 42},
    "includedPush": {"used": 3, "total": 100, "remaining": 97},
}

DATA_PUSH_JSON = {
    "requestId": "req_push_001",
    "tokenId": "BTC",
    "createdAt": "2026-03-09T12:00:00Z",
    "data": {"price": 62000, "signal": "GO"},
}


# ── Async tests ─────────────────────────────────────────────────────


class TestDataServiceAsync:
    @pytest.mark.asyncio
    async def test_get_latest(self) -> None:
        """get_latest returns a hydrated DataLatestResponse."""

        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json=LATEST_JSON)

        async with AttaGoClient(
            api_key="ak_test",
            base_url="https://api.test.com",
            transport=httpx.MockTransport(handler),
        ) as client:
            svc = DataService(client)
            result = await svc.get_latest()

        assert "BTC" in result.assets
        assert "ETH" in result.assets
        assert result.asset_order == ["BTC", "ETH"]
        assert result.market["totalCap"] == "2.1T"
        assert result.meta["schemaVersion"] == "4.0"

    @pytest.mark.asyncio
    async def test_get_latest_hits_correct_endpoint(self) -> None:
        """get_latest sends GET to /v1/data/latest."""
        captured_url = None

        def handler(request: httpx.Request) -> httpx.Response:
            nonlocal captured_url
            captured_url = str(request.url)
            return httpx.Response(200, json=LATEST_JSON)

        async with AttaGoClient(
            api_key="ak_test",
            base_url="https://api.test.com",
            transport=httpx.MockTransport(handler),
        ) as client:
            svc = DataService(client)
            await svc.get_latest()

        assert captured_url is not None
        assert "/v1/data/latest" in captured_url

    @pytest.mark.asyncio
    async def test_get_token_data(self) -> None:
        """get_token_data returns a hydrated DataTokenResponse with billing info."""

        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json=TOKEN_DATA_JSON)

        async with AttaGoClient(
            api_key="ak_test",
            base_url="https://api.test.com",
            transport=httpx.MockTransport(handler),
        ) as client:
            svc = DataService(client)
            result = await svc.get_token_data("BTC")

        assert result.token == "BTC"
        assert result.request_id == "req_tok789"
        assert result.mode == "testnet"
        assert result.has_derivatives is True
        assert result.deriv_symbols == ["BTCUSDT"]
        # Bundle usage
        assert result.bundle is not None
        assert result.bundle.bundle_id == "bun_001"
        assert result.bundle.remaining == 42
        # Included push usage
        assert result.included_push is not None
        assert result.included_push.used == 3
        assert result.included_push.remaining == 97

    @pytest.mark.asyncio
    async def test_get_token_data_hits_correct_endpoint(self) -> None:
        """get_token_data sends GET to /v1/api/data/{token}."""
        captured_url = None

        def handler(request: httpx.Request) -> httpx.Response:
            nonlocal captured_url
            captured_url = str(request.url)
            return httpx.Response(200, json=TOKEN_DATA_JSON)

        async with AttaGoClient(
            api_key="ak_test",
            base_url="https://api.test.com",
            transport=httpx.MockTransport(handler),
        ) as client:
            svc = DataService(client)
            await svc.get_token_data("ETH")

        assert captured_url is not None
        assert "/v1/api/data/ETH" in captured_url

    @pytest.mark.asyncio
    async def test_get_data_push(self) -> None:
        """get_data_push returns a hydrated DataPushResponse."""

        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json=DATA_PUSH_JSON)

        async with AttaGoClient(
            api_key="ak_test",
            base_url="https://api.test.com",
            transport=httpx.MockTransport(handler),
        ) as client:
            svc = DataService(client)
            result = await svc.get_data_push("req_push_001")

        assert result.request_id == "req_push_001"
        assert result.token_id == "BTC"
        assert result.created_at == "2026-03-09T12:00:00Z"
        assert result.data["signal"] == "GO"

    @pytest.mark.asyncio
    async def test_get_data_push_hits_correct_endpoint(self) -> None:
        """get_data_push sends GET to /v1/data/push/{requestId}."""
        captured_url = None

        def handler(request: httpx.Request) -> httpx.Response:
            nonlocal captured_url
            captured_url = str(request.url)
            return httpx.Response(200, json=DATA_PUSH_JSON)

        async with AttaGoClient(
            api_key="ak_test",
            base_url="https://api.test.com",
            transport=httpx.MockTransport(handler),
        ) as client:
            svc = DataService(client)
            await svc.get_data_push("req_xyz")

        assert captured_url is not None
        assert "/v1/data/push/req_xyz" in captured_url


# ── Sync tests ──────────────────────────────────────────────────────


class TestDataServiceSync:
    def test_get_latest_sync(self) -> None:
        """get_latest_sync returns a hydrated DataLatestResponse."""

        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json=LATEST_JSON)

        client = AttaGoClient(
            api_key="ak_test",
            base_url="https://api.test.com",
            sync=True,
            sync_transport=httpx.MockTransport(handler),
        )
        with client:
            svc = DataService(client)
            result = svc.get_latest_sync()

        assert "BTC" in result.assets
        assert result.asset_order == ["BTC", "ETH"]

    def test_get_token_data_sync(self) -> None:
        """get_token_data_sync returns a hydrated DataTokenResponse."""

        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json=TOKEN_DATA_JSON)

        client = AttaGoClient(
            api_key="ak_test",
            base_url="https://api.test.com",
            sync=True,
            sync_transport=httpx.MockTransport(handler),
        )
        with client:
            svc = DataService(client)
            result = svc.get_token_data_sync("BTC")

        assert result.token == "BTC"
        assert result.mode == "testnet"
        assert result.bundle is not None

    def test_get_data_push_sync(self) -> None:
        """get_data_push_sync returns a hydrated DataPushResponse."""

        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json=DATA_PUSH_JSON)

        client = AttaGoClient(
            api_key="ak_test",
            base_url="https://api.test.com",
            sync=True,
            sync_transport=httpx.MockTransport(handler),
        )
        with client:
            svc = DataService(client)
            result = svc.get_data_push_sync("req_push_001")

        assert result.request_id == "req_push_001"
        assert result.token_id == "BTC"
