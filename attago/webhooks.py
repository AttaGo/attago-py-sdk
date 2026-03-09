"""Webhook service -- CRUD, HMAC signing, and SDK-side test delivery."""

from __future__ import annotations

import hashlib
import hmac
import json
import uuid
from datetime import datetime, timezone
from typing import Any, TYPE_CHECKING

import httpx

if TYPE_CHECKING:
    from .client import AttaGoClient

from .types import (
    WebhookCreateResponse,
    WebhookListItem,
    WebhookTestResult,
    SendTestOptions,
)


class WebhookService:
    """Webhook management -- CRUD, SDK-side and server-side test delivery."""

    def __init__(self, client: AttaGoClient) -> None:
        self._client = client

    async def create(self, url: str) -> WebhookCreateResponse:
        """Create a new webhook.

        ``POST /webhooks``
        """
        if self._client._sync:
            data = self._client._request_sync("POST", "/webhooks", body={"url": url})
        else:
            data = await self._client._request("POST", "/webhooks", body={"url": url})
        return WebhookCreateResponse.from_dict(data)

    async def list(self) -> list[WebhookListItem]:
        """List all webhooks.

        ``GET /webhooks``
        """
        if self._client._sync:
            data = self._client._request_sync("GET", "/webhooks")
        else:
            data = await self._client._request("GET", "/webhooks")
        return [WebhookListItem.from_dict(w) for w in data.get("webhooks", [])]

    async def delete(self, webhook_id: str) -> None:
        """Delete a webhook.

        ``DELETE /webhooks/{webhook_id}``
        """
        if self._client._sync:
            self._client._request_sync("DELETE", f"/webhooks/{webhook_id}")
        else:
            await self._client._request("DELETE", f"/webhooks/{webhook_id}")

    async def send_server_test(self, webhook_id: str) -> WebhookTestResult:
        """Trigger a server-side test delivery.

        ``POST /webhooks/{webhook_id}/test``
        """
        if self._client._sync:
            data = self._client._request_sync(
                "POST", f"/webhooks/{webhook_id}/test"
            )
        else:
            data = await self._client._request(
                "POST", f"/webhooks/{webhook_id}/test"
            )
        return WebhookTestResult.from_dict(data)

    async def send_test(self, opts: SendTestOptions) -> WebhookTestResult:
        """SDK-side test delivery with retry.

        Builds a v2 test payload, signs it with HMAC, and POSTs to the
        webhook URL with exponential backoff [1s, 4s, 16s] (configurable).
        """
        payload = build_test_payload(
            token=opts.token,
            state=opts.state,
            environment=opts.environment,
        )
        body_bytes = json.dumps(payload, separators=(",", ":")).encode()
        signature = sign_payload(body_bytes, opts.secret)

        backoffs = opts.backoff_ms or [1000, 4000, 16000]
        max_attempts = len(backoffs) + 1

        last_error: str | None = None
        last_status: int | None = None

        for attempt in range(max_attempts):
            try:
                async with httpx.AsyncClient() as http:
                    resp = await http.post(
                        opts.url,
                        content=body_bytes,
                        headers={
                            "Content-Type": "application/json",
                            "X-AttaGo-Signature": signature,
                        },
                        timeout=10.0,
                    )
                last_status = resp.status_code
                if 200 <= resp.status_code < 300:
                    return WebhookTestResult(
                        success=True,
                        attempts=attempt + 1,
                        status_code=resp.status_code,
                    )
                last_error = f"HTTP {resp.status_code}"
            except Exception as exc:
                last_error = str(exc)

            # Wait before retry (skip wait after last attempt)
            if attempt < len(backoffs):
                await _async_sleep(backoffs[attempt] / 1000.0)

        return WebhookTestResult(
            success=False,
            attempts=max_attempts,
            status_code=last_status,
            error=last_error,
        )


async def _async_sleep(seconds: float) -> None:
    """Async sleep helper (easier to mock in tests)."""
    import asyncio

    await asyncio.sleep(seconds)


# -- Exported helpers --------------------------------------------------------


def build_test_payload(
    *,
    token: str = "BTC",
    state: str = "triggered",
    environment: str = "production",
    domain: str = "attago.bid",
) -> dict[str, Any]:
    """Build a v2 test webhook payload (matching TS/Go SDK)."""
    now = datetime.now(timezone.utc).isoformat()
    sub_id = f"sub_{uuid.uuid4().hex[:12]}"
    return {
        "event": "test",
        "version": "2",
        "environment": environment,
        "timestamp": now,
        "alert": {
            "id": sub_id,
            "label": f"SDK Test \u2013 {token}",
            "token": token,
            "state": state,
        },
        "data": {
            "url": f"https://{domain}/v1/data/push/test_{uuid.uuid4().hex[:8]}",
            "expiresAt": now,
            "fallbackUrl": None,
        },
    }


def sign_payload(body: bytes, secret: str) -> str:
    """HMAC-SHA256 sign a payload body with the webhook secret.

    Returns the hex digest string.
    """
    return hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


def verify_signature(body: bytes, secret: str, signature: str) -> bool:
    """Verify an HMAC-SHA256 webhook signature (constant-time comparison)."""
    expected = sign_payload(body, secret)
    return hmac.compare_digest(expected, signature)
