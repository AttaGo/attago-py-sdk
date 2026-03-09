"""Tests for attago.webhooks -- WebhookService, HMAC helpers, SDK-side delivery."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, patch

import httpx
import pytest

from attago.client import AttaGoClient
from attago.webhooks import (
    WebhookService,
    build_test_payload,
    sign_payload,
    verify_signature,
)
from attago.types import SendTestOptions, WebhookTestResult


# -- Helpers ----------------------------------------------------------------


def _make_client(handler) -> AttaGoClient:
    """Create an async AttaGoClient with a mock transport."""
    return AttaGoClient(
        api_key="ak_test",
        base_url="https://api.test.com",
        transport=httpx.MockTransport(handler),
    )


# -- Webhook helpers --------------------------------------------------------


class TestWebhookHelpers:
    def test_sign_payload_deterministic(self) -> None:
        """Same input produces the same HMAC signature."""
        body = b'{"event":"test"}'
        secret = "wh_secret_abc123"
        sig1 = sign_payload(body, secret)
        sig2 = sign_payload(body, secret)
        assert sig1 == sig2
        # Should be a 64-char hex string (SHA-256)
        assert len(sig1) == 64
        assert all(c in "0123456789abcdef" for c in sig1)

    def test_verify_signature_valid(self) -> None:
        """sign then verify with same secret returns True."""
        body = b'{"event":"test","version":"2"}'
        secret = "wh_secret_xyz"
        sig = sign_payload(body, secret)
        assert verify_signature(body, secret, sig) is True

    def test_verify_signature_invalid(self) -> None:
        """Wrong signature returns False."""
        body = b'{"event":"test"}'
        secret = "wh_secret_xyz"
        assert verify_signature(body, secret, "0000" * 16) is False

    def test_verify_signature_wrong_secret(self) -> None:
        """Signature from different secret returns False."""
        body = b'{"event":"test"}'
        sig = sign_payload(body, "secret_A")
        assert verify_signature(body, "secret_B", sig) is False

    def test_build_test_payload_structure(self) -> None:
        """Payload has event=test, version=2, alert, data, timestamp."""
        payload = build_test_payload()
        assert payload["event"] == "test"
        assert payload["version"] == "2"
        assert "timestamp" in payload
        # alert section
        alert = payload["alert"]
        assert "id" in alert
        assert alert["id"].startswith("sub_")
        assert alert["token"] == "BTC"
        assert alert["state"] == "triggered"
        assert "label" in alert
        # data section
        data = payload["data"]
        assert "url" in data
        assert data["url"].startswith("https://attago.bid/v1/data/push/test_")
        assert "expiresAt" in data
        assert "fallbackUrl" in data

    def test_build_test_payload_custom_token(self) -> None:
        """Custom token appears in payload alert."""
        payload = build_test_payload(token="ETH")
        assert payload["alert"]["token"] == "ETH"
        assert "ETH" in payload["alert"]["label"]

    def test_build_test_payload_custom_environment(self) -> None:
        """Custom environment appears in payload."""
        payload = build_test_payload(environment="staging")
        assert payload["environment"] == "staging"

    def test_build_test_payload_custom_state(self) -> None:
        """Custom state appears in payload alert."""
        payload = build_test_payload(state="resolved")
        assert payload["alert"]["state"] == "resolved"

    def test_build_test_payload_custom_domain(self) -> None:
        """Custom domain appears in data URL."""
        payload = build_test_payload(domain="staging.attago.io")
        assert payload["data"]["url"].startswith(
            "https://staging.attago.io/v1/data/push/test_"
        )


# -- WebhookService CRUD ---------------------------------------------------


class TestWebhookService:
    @pytest.mark.asyncio
    async def test_create(self) -> None:
        """POST /webhooks with url body, returns WebhookCreateResponse."""
        captured_body = None

        def handler(request: httpx.Request) -> httpx.Response:
            nonlocal captured_body
            assert request.method == "POST"
            assert "/v1/webhooks" in str(request.url)
            captured_body = json.loads(request.content)
            return httpx.Response(200, json={
                "webhookId": "wh_1",
                "url": "https://example.com/hook",
                "secret": "wh_secret_abc",
                "createdAt": "2026-03-01T00:00:00Z",
            })

        async with _make_client(handler) as client:
            svc = WebhookService(client)
            result = await svc.create("https://example.com/hook")

        assert result.webhook_id == "wh_1"
        assert result.url == "https://example.com/hook"
        assert result.secret == "wh_secret_abc"
        assert result.created_at == "2026-03-01T00:00:00Z"
        assert captured_body == {"url": "https://example.com/hook"}

    @pytest.mark.asyncio
    async def test_list(self) -> None:
        """GET /webhooks returns list[WebhookListItem]."""

        def handler(request: httpx.Request) -> httpx.Response:
            assert request.method == "GET"
            assert "/v1/webhooks" in str(request.url)
            return httpx.Response(200, json={
                "webhooks": [
                    {
                        "webhookId": "wh_1",
                        "url": "https://example.com/hook1",
                        "createdAt": "2026-03-01T00:00:00Z",
                    },
                    {
                        "webhookId": "wh_2",
                        "url": "https://example.com/hook2",
                        "createdAt": "2026-03-02T00:00:00Z",
                    },
                ]
            })

        async with _make_client(handler) as client:
            svc = WebhookService(client)
            result = await svc.list()

        assert len(result) == 2
        assert result[0].webhook_id == "wh_1"
        assert result[0].url == "https://example.com/hook1"
        assert result[1].webhook_id == "wh_2"

    @pytest.mark.asyncio
    async def test_list_empty(self) -> None:
        """GET /webhooks with empty list returns empty list."""

        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json={"webhooks": []})

        async with _make_client(handler) as client:
            svc = WebhookService(client)
            result = await svc.list()

        assert result == []

    @pytest.mark.asyncio
    async def test_delete(self) -> None:
        """DELETE /webhooks/{id} returns None (204)."""

        def handler(request: httpx.Request) -> httpx.Response:
            assert request.method == "DELETE"
            assert "/v1/webhooks/wh_1" in str(request.url)
            return httpx.Response(204)

        async with _make_client(handler) as client:
            svc = WebhookService(client)
            result = await svc.delete("wh_1")

        assert result is None

    @pytest.mark.asyncio
    async def test_send_server_test(self) -> None:
        """POST /webhooks/{id}/test returns WebhookTestResult."""

        def handler(request: httpx.Request) -> httpx.Response:
            assert request.method == "POST"
            assert "/v1/webhooks/wh_1/test" in str(request.url)
            return httpx.Response(200, json={
                "success": True,
                "attempts": 1,
                "statusCode": 200,
            })

        async with _make_client(handler) as client:
            svc = WebhookService(client)
            result = await svc.send_server_test("wh_1")

        assert result.success is True
        assert result.attempts == 1
        assert result.status_code == 200


# -- SDK-side send_test -----------------------------------------------------


class TestSendTest:
    @pytest.mark.asyncio
    async def test_send_test_success_first_attempt(self) -> None:
        """send_test succeeds on first attempt -- no retries, no sleep."""
        opts = SendTestOptions(
            url="https://example.com/hook",
            secret="wh_secret_test",
            token="BTC",
            state="triggered",
            environment="production",
            backoff_ms=[100, 200],
        )

        mock_response = httpx.Response(200)

        with patch("attago.webhooks.httpx.AsyncClient") as MockClient:
            instance = AsyncMock()
            instance.post.return_value = mock_response
            instance.__aenter__ = AsyncMock(return_value=instance)
            instance.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = instance

            with patch("attago.webhooks._async_sleep", new_callable=AsyncMock) as mock_sleep:
                # Need a real client just to call send_test on the service
                client = AttaGoClient(
                    api_key="ak_test",
                    base_url="https://api.test.com",
                    transport=httpx.MockTransport(lambda r: httpx.Response(200)),
                )
                svc = WebhookService(client)
                result = await svc.send_test(opts)
                await client.aclose()

        assert result.success is True
        assert result.attempts == 1
        assert result.status_code == 200
        assert result.error is None
        # No sleep on first-attempt success
        mock_sleep.assert_not_called()

    @pytest.mark.asyncio
    async def test_send_test_retries_on_failure(self) -> None:
        """send_test retries on non-2xx, returns failure after exhausting attempts."""
        opts = SendTestOptions(
            url="https://example.com/hook",
            secret="wh_secret_test",
            backoff_ms=[10, 20],  # 3 total attempts
        )

        mock_response = httpx.Response(500)

        with patch("attago.webhooks.httpx.AsyncClient") as MockClient:
            instance = AsyncMock()
            instance.post.return_value = mock_response
            instance.__aenter__ = AsyncMock(return_value=instance)
            instance.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = instance

            with patch("attago.webhooks._async_sleep", new_callable=AsyncMock) as mock_sleep:
                client = AttaGoClient(
                    api_key="ak_test",
                    base_url="https://api.test.com",
                    transport=httpx.MockTransport(lambda r: httpx.Response(200)),
                )
                svc = WebhookService(client)
                result = await svc.send_test(opts)
                await client.aclose()

        assert result.success is False
        assert result.attempts == 3  # 1 initial + 2 retries
        assert result.status_code == 500
        assert result.error == "HTTP 500"
        # Sleep called twice (between attempt 1->2, 2->3)
        assert mock_sleep.call_count == 2

    @pytest.mark.asyncio
    async def test_send_test_retries_then_succeeds(self) -> None:
        """send_test fails first attempt, succeeds on second."""
        opts = SendTestOptions(
            url="https://example.com/hook",
            secret="wh_secret_test",
            backoff_ms=[10, 20],
        )

        fail_resp = httpx.Response(503)
        ok_resp = httpx.Response(200)

        with patch("attago.webhooks.httpx.AsyncClient") as MockClient:
            instance = AsyncMock()
            # First call fails, second succeeds
            instance.post.side_effect = [fail_resp, ok_resp]
            instance.__aenter__ = AsyncMock(return_value=instance)
            instance.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = instance

            with patch("attago.webhooks._async_sleep", new_callable=AsyncMock) as mock_sleep:
                client = AttaGoClient(
                    api_key="ak_test",
                    base_url="https://api.test.com",
                    transport=httpx.MockTransport(lambda r: httpx.Response(200)),
                )
                svc = WebhookService(client)
                result = await svc.send_test(opts)
                await client.aclose()

        assert result.success is True
        assert result.attempts == 2
        assert result.status_code == 200
        # Slept once between attempt 1 and 2
        assert mock_sleep.call_count == 1

    @pytest.mark.asyncio
    async def test_send_test_exception_counts_as_failure(self) -> None:
        """Network exceptions count as failed attempts."""
        opts = SendTestOptions(
            url="https://example.com/hook",
            secret="wh_secret_test",
            backoff_ms=[10],  # 2 total attempts
        )

        with patch("attago.webhooks.httpx.AsyncClient") as MockClient:
            instance = AsyncMock()
            instance.post.side_effect = httpx.ConnectError("Connection refused")
            instance.__aenter__ = AsyncMock(return_value=instance)
            instance.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = instance

            with patch("attago.webhooks._async_sleep", new_callable=AsyncMock):
                client = AttaGoClient(
                    api_key="ak_test",
                    base_url="https://api.test.com",
                    transport=httpx.MockTransport(lambda r: httpx.Response(200)),
                )
                svc = WebhookService(client)
                result = await svc.send_test(opts)
                await client.aclose()

        assert result.success is False
        assert result.attempts == 2
        assert result.status_code is None
        assert "Connection refused" in result.error

    @pytest.mark.asyncio
    async def test_send_test_signs_payload(self) -> None:
        """send_test sends X-AttaGo-Signature header with correct HMAC."""
        opts = SendTestOptions(
            url="https://example.com/hook",
            secret="wh_secret_verify",
            backoff_ms=[],  # 1 attempt only
        )

        captured_headers: dict[str, str] = {}
        captured_body: bytes = b""

        with patch("attago.webhooks.httpx.AsyncClient") as MockClient:
            instance = AsyncMock()

            async def capture_post(url, *, content, headers, timeout):
                nonlocal captured_headers, captured_body
                captured_headers = dict(headers)
                captured_body = content
                return httpx.Response(200)

            instance.post = capture_post
            instance.__aenter__ = AsyncMock(return_value=instance)
            instance.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = instance

            with patch("attago.webhooks._async_sleep", new_callable=AsyncMock):
                client = AttaGoClient(
                    api_key="ak_test",
                    base_url="https://api.test.com",
                    transport=httpx.MockTransport(lambda r: httpx.Response(200)),
                )
                svc = WebhookService(client)
                result = await svc.send_test(opts)
                await client.aclose()

        assert result.success is True
        assert "X-AttaGo-Signature" in captured_headers
        # Verify the signature matches what sign_payload would produce
        expected_sig = sign_payload(captured_body, "wh_secret_verify")
        assert captured_headers["X-AttaGo-Signature"] == expected_sig
