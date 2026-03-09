"""Core HTTP client for the AttaGo Python SDK.

Mirrors the Go SDK's ``client.go``:
- Single auth mode validation (api_key | signer | cognito)
- ``/v1`` path prefix normalisation
- Typed error mapping (402, 429, generic)
- x402 auto-retry for signer mode
- Async-first with opt-in sync mode
"""

from __future__ import annotations

import json
from typing import Any

import httpx

from .errors import ApiError, PaymentRequiredError, RateLimitError
from .types import DEFAULT_BASE_URL, DEFAULT_COGNITO_REGION, VERSION
from .x402 import do_with_x402, parse_payment_required

from .agent import AgentService
from .data import DataService
from .subscriptions import SubscriptionService
from .payments import PaymentService
from .wallets import WalletService
from .webhooks import WebhookService
from .mcp import McpService
from .api_keys import ApiKeyService
from .bundles import BundleService
from .push import PushService
from .redeem import RedeemService


# ── Auth modes ───────────────────────────────────────────────────────

AUTH_MODE_API_KEY = "apikey"
AUTH_MODE_X402 = "x402"
AUTH_MODE_COGNITO = "cognito"
AUTH_MODE_NONE = "none"


# ── Client ───────────────────────────────────────────────────────────


class AttaGoClient:
    """AttaGo API client.

    Only one authentication mode is allowed at a time:

    - **API key**: ``AttaGoClient(api_key="ak_live_...")``
    - **x402 signer**: ``AttaGoClient(signer=my_signer)``
    - **Cognito**: ``AttaGoClient(email="...", password="...", cognito_client_id="...")``

    Parameters
    ----------
    api_key:
        API key for header-based authentication.
    signer:
        :class:`X402Signer` for x402 payment-authenticated requests.
    email, password, cognito_client_id, cognito_region:
        Cognito email/password authentication (requires ``cognito_client_id``).
    base_url:
        Override the default API base URL.
    transport:
        Custom ``httpx.AsyncBaseTransport`` (for testing with ``MockTransport``).
    sync_transport:
        Custom ``httpx.BaseTransport`` (for sync-mode testing).
    sync:
        If ``True``, use ``httpx.Client`` instead of ``httpx.AsyncClient``.
    """

    def __init__(
        self,
        *,
        api_key: str | None = None,
        signer: Any | None = None,
        email: str | None = None,
        password: str | None = None,
        cognito_client_id: str | None = None,
        cognito_region: str = DEFAULT_COGNITO_REGION,
        base_url: str = DEFAULT_BASE_URL,
        transport: httpx.AsyncBaseTransport | None = None,
        sync_transport: httpx.BaseTransport | None = None,
        sync: bool = False,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._signer = signer
        self._cognito_email = email
        self._cognito_password = password
        self._cognito_client_id = cognito_client_id
        self._cognito_region = cognito_region
        self._sync = sync

        # ── Validate: at most one auth mode ──
        modes = 0
        if api_key:
            modes += 1
        if signer is not None:
            modes += 1
        if email or cognito_client_id:
            modes += 1
        if modes > 1:
            raise ValueError(
                "Only one auth mode allowed (api_key, signer, or cognito)"
            )

        # ── Cognito requires client_id ──
        if self.auth_mode == AUTH_MODE_COGNITO and not cognito_client_id:
            raise ValueError(
                "cognito_client_id is required for Cognito authentication"
            )

        # ── HTTP clients ──
        user_agent = f"attago-python/{VERSION}"
        common_headers = {
            "Accept": "application/json",
            "User-Agent": user_agent,
        }

        if sync:
            self._sync_client: httpx.Client | None = httpx.Client(
                headers=common_headers,
                transport=sync_transport,
            )
            self._async_client: httpx.AsyncClient | None = None
        else:
            self._async_client = httpx.AsyncClient(
                headers=common_headers,
                transport=transport,
            )
            self._sync_client = None

        # ── Attach service namespaces ──
        self.agent = AgentService(self)
        self.data = DataService(self)
        self.subscriptions = SubscriptionService(self)
        self.payments = PaymentService(self)
        self.wallets = WalletService(self)
        self.webhooks = WebhookService(self)
        self.mcp = McpService(self)
        self.api_keys = ApiKeyService(self)
        self.bundles = BundleService(self)
        self.push = PushService(self)
        self.redeem = RedeemService(self)

    # ── Auth mode ────────────────────────────────────────────────────

    @property
    def auth_mode(self) -> str:
        """Return the active authentication mode string."""
        if self._api_key:
            return AUTH_MODE_API_KEY
        if self._signer is not None:
            return AUTH_MODE_X402
        if self._cognito_email or self._cognito_client_id:
            return AUTH_MODE_COGNITO
        return AUTH_MODE_NONE

    @property
    def signer(self) -> Any | None:
        """Return the configured x402 signer, or ``None``."""
        return self._signer

    # ── Path normalisation ───────────────────────────────────────────

    @staticmethod
    def _normalise_path(path: str) -> str:
        """Ensure *path* starts with ``/v1/``."""
        if not path.startswith("/"):
            path = "/" + path
        if not path.startswith("/v1/"):
            path = "/v1" + path
        return path

    # ── Auth headers ─────────────────────────────────────────────────

    def _auth_headers(self) -> dict[str, str]:
        """Build auth headers for the current auth mode."""
        if self.auth_mode == AUTH_MODE_API_KEY:
            return {"X-API-Key": self._api_key}  # type: ignore[dict-item]
        # Cognito and x402 don't add headers here -- Cognito would add
        # a Bearer token (not yet implemented), x402 is handled by
        # do_with_x402.
        return {}

    # ── Async request ────────────────────────────────────────────────

    async def _request(
        self,
        method: str,
        path: str,
        *,
        body: Any | None = None,
        params: dict[str, str] | None = None,
        headers: dict[str, str] | None = None,
    ) -> Any:
        """Execute an authenticated HTTP request and return decoded JSON.

        Mirrors the Go SDK's ``do()`` method:
        1. Normalise path (add ``/v1`` prefix if missing).
        2. Build full URL.
        3. Add auth headers.
        4. For x402 mode: delegate to ``do_with_x402`` for auto-retry.
        5. On non-2xx: raise typed error.
        6. On 204: return ``None``.
        7. Otherwise: return parsed JSON.
        """
        if self._async_client is None:
            raise RuntimeError(
                "Cannot use async _request() with sync=True client"
            )

        path = self._normalise_path(path)
        url = self.base_url + path

        # ── Headers ──
        req_headers = self._auth_headers()
        if headers:
            req_headers.update(headers)

        # ── Body ──
        content: bytes | None = None
        if body is not None:
            content = json.dumps(body).encode()
            req_headers["Content-Type"] = "application/json"

        # ── Execute ──
        if self.auth_mode == AUTH_MODE_X402 and self._signer is not None:
            response = await do_with_x402(
                self._async_client,
                self._signer,
                method,
                url,
                headers=req_headers,
                content=content,
            )
        else:
            response = await self._async_client.request(
                method,
                url,
                headers=req_headers,
                content=content,
                params=params,
            )

        # ── Handle errors ──
        if response.status_code >= 400:
            self._handle_error(response)

        # ── 204 No Content ──
        if response.status_code == 204:
            return None

        return response.json()

    # ── Sync request ─────────────────────────────────────────────────

    def _request_sync(
        self,
        method: str,
        path: str,
        *,
        body: Any | None = None,
        params: dict[str, str] | None = None,
        headers: dict[str, str] | None = None,
    ) -> Any:
        """Synchronous version of :meth:`_request`.

        Only available when the client was created with ``sync=True``.
        """
        if self._sync_client is None:
            raise RuntimeError(
                "Cannot use _request_sync() with async client"
            )

        path = self._normalise_path(path)
        url = self.base_url + path

        # ── Headers ──
        req_headers = self._auth_headers()
        if headers:
            req_headers.update(headers)

        # ── Body ──
        content: bytes | None = None
        if body is not None:
            content = json.dumps(body).encode()
            req_headers["Content-Type"] = "application/json"

        # ── Execute ──
        response = self._sync_client.request(
            method,
            url,
            headers=req_headers,
            content=content,
            params=params,
        )

        # ── Handle errors ──
        if response.status_code >= 400:
            self._handle_error(response)

        # ── 204 No Content ──
        if response.status_code == 204:
            return None

        return response.json()

    # ── Error mapping ────────────────────────────────────────────────

    @staticmethod
    def _handle_error(response: httpx.Response) -> None:
        """Map an error HTTP response to a typed exception.

        Mirrors the Go SDK's ``handleHTTPError``.
        """
        body: dict[str, Any] = {}
        try:
            body = response.json()
        except Exception:
            pass

        message = (
            body.get("error")
            or body.get("message")
            or f"HTTP {response.status_code}"
        )

        resp_headers = dict(response.headers)

        if response.status_code == 402:
            reqs = parse_payment_required(response.headers)
            raise PaymentRequiredError(
                message=message,
                body=body,
                headers=resp_headers,
                payment_requirements=reqs,
            )

        if response.status_code == 429:
            retry_after: int | None = None
            raw = response.headers.get("retry-after")
            if raw:
                try:
                    retry_after = int(raw)
                except ValueError:
                    pass
            raise RateLimitError(
                message=message,
                body=body,
                headers=resp_headers,
                retry_after=retry_after,
            )

        raise ApiError(
            status_code=response.status_code,
            message=message,
            body=body,
            headers=resp_headers,
        )

    # ── Context manager ──────────────────────────────────────────────

    async def __aenter__(self) -> AttaGoClient:
        return self

    async def __aexit__(self, *exc: Any) -> None:
        await self.aclose()

    def __enter__(self) -> AttaGoClient:
        return self

    def __exit__(self, *exc: Any) -> None:
        self.close()

    async def aclose(self) -> None:
        """Close the underlying async HTTP client."""
        if self._async_client is not None:
            await self._async_client.aclose()

    def close(self) -> None:
        """Close the underlying sync HTTP client."""
        if self._sync_client is not None:
            self._sync_client.close()
