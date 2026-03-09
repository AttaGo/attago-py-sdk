"""Tests for attago.x402 -- x402 payment protocol helpers."""

from __future__ import annotations

import base64
import json

import httpx
import pytest

from attago.errors import PaymentRequiredError
from attago.x402 import (
    do_with_x402,
    filter_accepts_by_network,
    parse_payment_required,
)


# ── Fixtures ─────────────────────────────────────────────────────────

SAMPLE_REQUIREMENTS = {
    "x402Version": 1,
    "resource": {
        "url": "https://api.attago.bid/v1/agent/score",
        "description": "Go/No-Go score for BTC",
        "mimeType": "application/json",
    },
    "accepts": [
        {
            "scheme": "exact",
            "network": "eip155:8453",
            "amount": "100000",
            "asset": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
            "payTo": "0xDEAD",
            "maxTimeoutSeconds": 30,
        },
        {
            "scheme": "exact",
            "network": "solana:mainnet",
            "amount": "100000",
            "asset": "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
            "payTo": "SomeSOLAddress",
            "maxTimeoutSeconds": 30,
        },
    ],
}


def _encode_requirements(reqs: dict) -> str:
    """Base64-encode requirements for the Payment-Required header."""
    return base64.b64encode(json.dumps(reqs).encode()).decode()


class FakeSigner:
    """Minimal x402 signer for testing."""

    def __init__(self, net: str = "eip155:8453") -> None:
        self.address = "0xTESTADDRESS"
        self.network = net

    async def sign(self, requirements: dict) -> str:
        return "signed-payment-base64"


# ── parse_payment_required ───────────────────────────────────────────


class TestParsePaymentRequired:
    def test_parse_payment_required_valid(self) -> None:
        encoded = _encode_requirements(SAMPLE_REQUIREMENTS)
        headers = {"Payment-Required": encoded}
        result = parse_payment_required(headers)
        assert result is not None
        assert result["x402Version"] == 1
        assert len(result["accepts"]) == 2

    def test_parse_payment_required_valid_lowercase(self) -> None:
        """Works with lowercase header name (httpx normalisation)."""
        encoded = _encode_requirements(SAMPLE_REQUIREMENTS)
        headers = {"payment-required": encoded}
        result = parse_payment_required(headers)
        assert result is not None
        assert result["x402Version"] == 1

    def test_parse_payment_required_missing(self) -> None:
        headers: dict[str, str] = {}
        result = parse_payment_required(headers)
        assert result is None

    def test_parse_payment_required_invalid(self) -> None:
        headers = {"Payment-Required": "not-valid-base64!!!"}
        result = parse_payment_required(headers)
        assert result is None

    def test_parse_payment_required_urlsafe_b64(self) -> None:
        """Falls back to URL-safe base64 decoding."""
        raw = json.dumps(SAMPLE_REQUIREMENTS).encode()
        encoded = base64.urlsafe_b64encode(raw).decode()
        headers = {"Payment-Required": encoded}
        result = parse_payment_required(headers)
        assert result is not None
        assert result["x402Version"] == 1


# ── filter_accepts_by_network ────────────────────────────────────────


class TestFilterAcceptsByNetwork:
    def test_filter_accepts_found(self) -> None:
        accepts = SAMPLE_REQUIREMENTS["accepts"]
        result = filter_accepts_by_network(accepts, "eip155:8453")
        assert result is not None
        assert result["network"] == "eip155:8453"

    def test_filter_accepts_not_found(self) -> None:
        accepts = SAMPLE_REQUIREMENTS["accepts"]
        result = filter_accepts_by_network(accepts, "eip155:999")
        assert result is None

    def test_filter_accepts_solana(self) -> None:
        accepts = SAMPLE_REQUIREMENTS["accepts"]
        result = filter_accepts_by_network(accepts, "solana:mainnet")
        assert result is not None
        assert result["network"] == "solana:mainnet"


# ── do_with_x402 ─────────────────────────────────────────────────────


class TestDoWithX402:
    @pytest.mark.asyncio
    async def test_non_402_passthrough(self) -> None:
        """Non-402 responses pass through without signing."""

        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json={"ok": True})

        async with httpx.AsyncClient(
            transport=httpx.MockTransport(handler),
        ) as client:
            resp = await do_with_x402(
                client,
                FakeSigner(),
                "GET",
                "https://api.test.com/v1/agent/score",
            )
            assert resp.status_code == 200
            assert resp.json() == {"ok": True}

    @pytest.mark.asyncio
    async def test_auto_retry(self) -> None:
        """On 402, signs and retries with Payment-Signature header."""
        call_count = 0

        def handler(request: httpx.Request) -> httpx.Response:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                # First request: return 402 with payment requirements
                encoded = _encode_requirements(SAMPLE_REQUIREMENTS)
                return httpx.Response(
                    402,
                    json={"error": "Payment required"},
                    headers={"Payment-Required": encoded},
                )
            # Retry: verify signature header and return success
            assert request.headers.get("payment-signature") == "signed-payment-base64"
            return httpx.Response(200, json={"paid": True})

        async with httpx.AsyncClient(
            transport=httpx.MockTransport(handler),
        ) as client:
            resp = await do_with_x402(
                client,
                FakeSigner("eip155:8453"),
                "GET",
                "https://api.test.com/v1/agent/score",
            )
            assert resp.status_code == 200
            assert resp.json() == {"paid": True}
            assert call_count == 2

    @pytest.mark.asyncio
    async def test_no_matching_network(self) -> None:
        """Raises PaymentRequiredError when signer's network has no match."""

        def handler(request: httpx.Request) -> httpx.Response:
            encoded = _encode_requirements(SAMPLE_REQUIREMENTS)
            return httpx.Response(
                402,
                json={"error": "Payment required"},
                headers={"Payment-Required": encoded},
            )

        async with httpx.AsyncClient(
            transport=httpx.MockTransport(handler),
        ) as client:
            with pytest.raises(PaymentRequiredError, match="No accepted payment"):
                await do_with_x402(
                    client,
                    FakeSigner("eip155:999"),  # no match
                    "GET",
                    "https://api.test.com/v1/agent/score",
                )

    @pytest.mark.asyncio
    async def test_unparseable_requirements(self) -> None:
        """Raises PaymentRequiredError when Payment-Required header is missing."""

        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                402,
                json={"error": "Payment required"},
                # No Payment-Required header
            )

        async with httpx.AsyncClient(
            transport=httpx.MockTransport(handler),
        ) as client:
            with pytest.raises(PaymentRequiredError, match="unparseable"):
                await do_with_x402(
                    client,
                    FakeSigner(),
                    "GET",
                    "https://api.test.com/v1/agent/score",
                )

    @pytest.mark.asyncio
    async def test_retry_also_402_raises(self) -> None:
        """If the retry also returns 402, raise PaymentRequiredError."""

        def handler(request: httpx.Request) -> httpx.Response:
            encoded = _encode_requirements(SAMPLE_REQUIREMENTS)
            return httpx.Response(
                402,
                json={"error": "Payment required"},
                headers={"Payment-Required": encoded},
            )

        async with httpx.AsyncClient(
            transport=httpx.MockTransport(handler),
        ) as client:
            with pytest.raises(PaymentRequiredError, match="rejected after signing"):
                await do_with_x402(
                    client,
                    FakeSigner("eip155:8453"),
                    "GET",
                    "https://api.test.com/v1/agent/score",
                )

    @pytest.mark.asyncio
    async def test_params_forwarded_through_x402(self) -> None:
        """Query params survive both the initial request and the signed retry."""
        captured_urls: list[str] = []
        call_count = 0

        def handler(request: httpx.Request) -> httpx.Response:
            nonlocal call_count
            call_count += 1
            captured_urls.append(str(request.url))
            if call_count == 1:
                encoded = _encode_requirements(SAMPLE_REQUIREMENTS)
                return httpx.Response(
                    402,
                    json={"error": "Payment required"},
                    headers={"Payment-Required": encoded},
                )
            return httpx.Response(200, json={"paid": True})

        async with httpx.AsyncClient(
            transport=httpx.MockTransport(handler),
        ) as client:
            resp = await do_with_x402(
                client,
                FakeSigner("eip155:8453"),
                "GET",
                "https://api.test.com/v1/agent/score",
                params={"token": "BTC"},
            )
            assert resp.status_code == 200
            assert call_count == 2
            # Both the initial 402 request and the signed retry must include params
            for url in captured_urls:
                assert "token=BTC" in url
