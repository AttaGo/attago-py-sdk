"""Tests for attago.client -- AttaGoClient core HTTP client."""

from __future__ import annotations

import json

import httpx
import pytest
import pytest_asyncio

from attago.client import (
    AUTH_MODE_API_KEY,
    AUTH_MODE_COGNITO,
    AUTH_MODE_NONE,
    AUTH_MODE_X402,
    AttaGoClient,
)
from attago.errors import ApiError, PaymentRequiredError, RateLimitError
from attago.types import DEFAULT_BASE_URL


# ── Helpers ──────────────────────────────────────────────────────────


def _ok_handler(request: httpx.Request) -> httpx.Response:
    """Return 200 with an echo of method and url."""
    return httpx.Response(
        200,
        json={"method": str(request.method), "url": str(request.url)},
    )


def _echo_handler(request: httpx.Request) -> httpx.Response:
    """Echo back request details for inspection."""
    headers_dict = dict(request.headers)
    body = None
    if request.content:
        body = json.loads(request.content)
    return httpx.Response(
        200,
        json={
            "method": str(request.method),
            "url": str(request.url),
            "headers": headers_dict,
            "body": body,
        },
    )


# ── Construction & Auth Mode ────────────────────────────────────────


class TestClientConstruction:
    def test_default_base_url(self) -> None:
        client = AttaGoClient(
            transport=httpx.MockTransport(_ok_handler),
        )
        assert client.base_url == DEFAULT_BASE_URL

    def test_custom_base_url(self) -> None:
        client = AttaGoClient(
            base_url="https://custom.example.com/",
            transport=httpx.MockTransport(_ok_handler),
        )
        # Trailing slash stripped
        assert client.base_url == "https://custom.example.com"

    def test_auth_mode_api_key(self) -> None:
        client = AttaGoClient(
            api_key="ak_test_123",
            transport=httpx.MockTransport(_ok_handler),
        )
        assert client.auth_mode == AUTH_MODE_API_KEY

    def test_auth_mode_none(self) -> None:
        client = AttaGoClient(
            transport=httpx.MockTransport(_ok_handler),
        )
        assert client.auth_mode == AUTH_MODE_NONE

    def test_auth_mode_x402(self) -> None:
        class FakeSigner:
            def address(self) -> str:
                return "0xabc"

            def network(self) -> str:
                return "eip155:8453"

            async def sign(self, requirements):
                return "sig"

        client = AttaGoClient(
            signer=FakeSigner(),
            transport=httpx.MockTransport(_ok_handler),
        )
        assert client.auth_mode == AUTH_MODE_X402

    def test_auth_mode_cognito(self) -> None:
        client = AttaGoClient(
            email="user@example.com",
            password="secret",
            cognito_client_id="abc123",
            transport=httpx.MockTransport(_ok_handler),
        )
        assert client.auth_mode == AUTH_MODE_COGNITO

    def test_multiple_auth_modes_raises(self) -> None:
        with pytest.raises(ValueError, match="Only one auth mode"):
            AttaGoClient(
                api_key="ak_test_123",
                email="user@example.com",
                cognito_client_id="abc",
                transport=httpx.MockTransport(_ok_handler),
            )

    def test_cognito_without_client_id_raises(self) -> None:
        with pytest.raises(ValueError, match="cognito_client_id is required"):
            AttaGoClient(
                email="user@example.com",
                password="secret",
                transport=httpx.MockTransport(_ok_handler),
            )


# ── Request Mechanics ────────────────────────────────────────────────


class TestRequestMechanics:
    @pytest.mark.asyncio
    async def test_v1_prefix_added(self) -> None:
        """Paths without /v1/ get the prefix prepended."""
        async with AttaGoClient(
            base_url="https://api.test.com",
            transport=httpx.MockTransport(_echo_handler),
        ) as client:
            result = await client._request("GET", "/agent/score")
            assert "/v1/agent/score" in result["url"]

    @pytest.mark.asyncio
    async def test_v1_prefix_preserved(self) -> None:
        """Paths already starting with /v1/ are not double-prefixed."""
        async with AttaGoClient(
            base_url="https://api.test.com",
            transport=httpx.MockTransport(_echo_handler),
        ) as client:
            result = await client._request("GET", "/v1/agent/score")
            assert "/v1/v1/" not in result["url"]
            assert "/v1/agent/score" in result["url"]

    @pytest.mark.asyncio
    async def test_api_key_header_sent(self) -> None:
        async with AttaGoClient(
            api_key="ak_test_hello",
            base_url="https://api.test.com",
            transport=httpx.MockTransport(_echo_handler),
        ) as client:
            result = await client._request("GET", "/agent/score")
            assert result["headers"]["x-api-key"] == "ak_test_hello"

    @pytest.mark.asyncio
    async def test_user_agent_sent(self) -> None:
        async with AttaGoClient(
            base_url="https://api.test.com",
            transport=httpx.MockTransport(_echo_handler),
        ) as client:
            result = await client._request("GET", "/ping")
            assert "attago-python/" in result["headers"]["user-agent"]

    @pytest.mark.asyncio
    async def test_json_body_sent(self) -> None:
        async with AttaGoClient(
            base_url="https://api.test.com",
            transport=httpx.MockTransport(_echo_handler),
        ) as client:
            result = await client._request(
                "POST", "/data", body={"token": "BTC"}
            )
            assert result["body"] == {"token": "BTC"}
            assert result["headers"]["content-type"] == "application/json"

    @pytest.mark.asyncio
    async def test_query_params(self) -> None:
        async with AttaGoClient(
            base_url="https://api.test.com",
            transport=httpx.MockTransport(_echo_handler),
        ) as client:
            result = await client._request(
                "GET", "/data", params={"token": "ETH"}
            )
            assert "token=ETH" in result["url"]


# ── Response Handling ────────────────────────────────────────────────


class TestResponseHandling:
    @pytest.mark.asyncio
    async def test_204_returns_none(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(204)

        async with AttaGoClient(
            base_url="https://api.test.com",
            transport=httpx.MockTransport(handler),
        ) as client:
            result = await client._request("DELETE", "/something")
            assert result is None

    @pytest.mark.asyncio
    async def test_404_raises_api_error(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(404, json={"error": "Not found"})

        async with AttaGoClient(
            base_url="https://api.test.com",
            transport=httpx.MockTransport(handler),
        ) as client:
            with pytest.raises(ApiError) as exc_info:
                await client._request("GET", "/missing")
            assert exc_info.value.status_code == 404
            assert exc_info.value.message == "Not found"

    @pytest.mark.asyncio
    async def test_429_raises_rate_limit_error(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                429,
                json={"error": "Too many requests"},
                headers={"retry-after": "30"},
            )

        async with AttaGoClient(
            base_url="https://api.test.com",
            transport=httpx.MockTransport(handler),
        ) as client:
            with pytest.raises(RateLimitError) as exc_info:
                await client._request("GET", "/data")
            assert exc_info.value.status_code == 429
            assert exc_info.value.retry_after == 30

    @pytest.mark.asyncio
    async def test_402_raises_payment_required_error(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                402, json={"error": "Payment required"}
            )

        async with AttaGoClient(
            base_url="https://api.test.com",
            transport=httpx.MockTransport(handler),
        ) as client:
            with pytest.raises(PaymentRequiredError) as exc_info:
                await client._request("GET", "/agent/score")
            assert exc_info.value.status_code == 402

    @pytest.mark.asyncio
    async def test_500_raises_api_error(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                500, json={"error": "Internal server error"}
            )

        async with AttaGoClient(
            base_url="https://api.test.com",
            transport=httpx.MockTransport(handler),
        ) as client:
            with pytest.raises(ApiError) as exc_info:
                await client._request("GET", "/broken")
            assert exc_info.value.status_code == 500

    @pytest.mark.asyncio
    async def test_error_message_from_message_field(self) -> None:
        """Falls back to 'message' key when 'error' key is absent."""
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                403, json={"message": "Forbidden access"}
            )

        async with AttaGoClient(
            base_url="https://api.test.com",
            transport=httpx.MockTransport(handler),
        ) as client:
            with pytest.raises(ApiError) as exc_info:
                await client._request("GET", "/secret")
            assert exc_info.value.message == "Forbidden access"


# ── Context Manager ──────────────────────────────────────────────────


class TestContextManager:
    @pytest.mark.asyncio
    async def test_context_manager_closes(self) -> None:
        """Async context manager closes the underlying client."""
        client = AttaGoClient(
            base_url="https://api.test.com",
            transport=httpx.MockTransport(_ok_handler),
        )
        async with client:
            result = await client._request("GET", "/ping")
            assert result is not None

        # After exit, the client should be closed.
        assert client._async_client is not None
        assert client._async_client.is_closed


# ── Sync Mode ────────────────────────────────────────────────────────


class TestSyncMode:
    def test_sync_mode_request(self) -> None:
        client = AttaGoClient(
            api_key="ak_sync_test",
            base_url="https://api.test.com",
            sync=True,
            sync_transport=httpx.MockTransport(_echo_handler),
        )
        with client:
            result = client._request_sync("GET", "/agent/score")
            assert "/v1/agent/score" in result["url"]
            assert result["headers"]["x-api-key"] == "ak_sync_test"
            assert "attago-python/" in result["headers"]["user-agent"]

    def test_sync_mode_204(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(204)

        client = AttaGoClient(
            base_url="https://api.test.com",
            sync=True,
            sync_transport=httpx.MockTransport(handler),
        )
        with client:
            result = client._request_sync("DELETE", "/something")
            assert result is None

    def test_sync_mode_error(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(500, json={"error": "boom"})

        client = AttaGoClient(
            base_url="https://api.test.com",
            sync=True,
            sync_transport=httpx.MockTransport(handler),
        )
        with client:
            with pytest.raises(ApiError) as exc_info:
                client._request_sync("GET", "/broken")
            assert exc_info.value.status_code == 500
