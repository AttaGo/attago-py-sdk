"""Tests for the 7 service modules (Task 6).

Covers: SubscriptionService, PaymentService, WalletService, ApiKeyService,
BundleService, PushService, RedeemService.
"""

from __future__ import annotations

import json

import httpx
import pytest

from attago.client import AttaGoClient
from attago.subscriptions import SubscriptionService
from attago.payments import PaymentService
from attago.wallets import WalletService
from attago.api_keys import ApiKeyService
from attago.bundles import BundleService
from attago.push import PushService
from attago.redeem import RedeemService
from attago.types import (
    CreatePushInput,
    CreateSubscriptionInput,
    PurchaseBundleInput,
    PushKeys,
    RegisterWalletInput,
    SubscribeInput,
    SubscriptionCondition,
    UpdateSubscriptionInput,
)


# ── Helpers ────────────────────────────────────────────────────────


def _make_client(handler) -> AttaGoClient:
    """Create an async AttaGoClient with a mock transport."""
    return AttaGoClient(
        api_key="ak_test",
        base_url="https://api.test.com",
        transport=httpx.MockTransport(handler),
    )


# ── SubscriptionService ──────────────────────────────────────────


class TestSubscriptionService:
    @pytest.mark.asyncio
    async def test_catalog(self) -> None:
        """catalog() returns a CatalogResponse with tokens and metrics."""

        def handler(request: httpx.Request) -> httpx.Response:
            assert "/v1/subscriptions/catalog" in str(request.url)
            return httpx.Response(200, json={
                "tokens": ["BTC", "ETH"],
                "metrics": {
                    "compositeScore": {
                        "label": "Composite Score",
                        "type": "number",
                        "operators": ["gt", "lt"],
                    }
                },
                "tier": "free",
                "maxSubscriptions": 5,
                "mode": "live",
            })

        async with _make_client(handler) as client:
            svc = SubscriptionService(client)
            result = await svc.catalog()

        assert result.tier == "free"
        assert "BTC" in result.tokens
        assert "compositeScore" in result.metrics
        assert result.metrics["compositeScore"].label == "Composite Score"
        assert result.max_subscriptions == 5

    @pytest.mark.asyncio
    async def test_list(self) -> None:
        """list() returns a list of Subscription objects."""

        def handler(request: httpx.Request) -> httpx.Response:
            assert "/v1/subscriptions" in str(request.url)
            assert request.method == "GET"
            return httpx.Response(200, json={
                "subscriptions": [
                    {
                        "userId": "u1",
                        "subId": "sub_1",
                        "tokenId": "BTC",
                        "label": "BTC alert",
                        "groups": [[{
                            "metricName": "compositeScore",
                            "thresholdOp": "gt",
                            "thresholdVal": 70,
                        }]],
                        "cooldownMinutes": 10,
                        "bucketHash": "abc123",
                        "isActive": True,
                        "createdAt": "2026-01-01T00:00:00Z",
                        "updatedAt": "2026-01-01T00:00:00Z",
                    }
                ]
            })

        async with _make_client(handler) as client:
            svc = SubscriptionService(client)
            result = await svc.list()

        assert len(result) == 1
        assert result[0].sub_id == "sub_1"
        assert result[0].token_id == "BTC"
        assert result[0].is_active is True

    @pytest.mark.asyncio
    async def test_create(self) -> None:
        """create() sends correct body and returns a Subscription."""
        captured_body = None

        def handler(request: httpx.Request) -> httpx.Response:
            nonlocal captured_body
            assert request.method == "POST"
            captured_body = json.loads(request.content)
            return httpx.Response(200, json={
                "userId": "u1",
                "subId": "sub_new",
                "tokenId": "ETH",
                "label": "ETH dip",
                "groups": [[{
                    "metricName": "spotPrice",
                    "thresholdOp": "lt",
                    "thresholdVal": 3000,
                }]],
                "cooldownMinutes": 15,
                "bucketHash": "def456",
                "isActive": True,
                "createdAt": "2026-03-01T00:00:00Z",
                "updatedAt": "2026-03-01T00:00:00Z",
            })

        input_data = CreateSubscriptionInput(
            token_id="ETH",
            label="ETH dip",
            groups=[[
                SubscriptionCondition(
                    metric_name="spotPrice",
                    threshold_op="lt",
                    threshold_val=3000,
                )
            ]],
            cooldown_minutes=15,
        )

        async with _make_client(handler) as client:
            svc = SubscriptionService(client)
            result = await svc.create(input_data)

        assert result.sub_id == "sub_new"
        assert result.token_id == "ETH"
        assert captured_body["tokenId"] == "ETH"
        assert captured_body["label"] == "ETH dip"
        assert captured_body["cooldownMinutes"] == 15
        assert captured_body["groups"][0][0]["metricName"] == "spotPrice"

    @pytest.mark.asyncio
    async def test_create_no_cooldown(self) -> None:
        """create() omits cooldownMinutes when not set."""
        captured_body = None

        def handler(request: httpx.Request) -> httpx.Response:
            nonlocal captured_body
            captured_body = json.loads(request.content)
            return httpx.Response(200, json={
                "userId": "u1",
                "subId": "sub_2",
                "tokenId": "BTC",
                "label": "BTC alert",
                "groups": [],
                "cooldownMinutes": 5,
                "bucketHash": "x",
                "isActive": True,
                "createdAt": "2026-03-01T00:00:00Z",
                "updatedAt": "2026-03-01T00:00:00Z",
            })

        input_data = CreateSubscriptionInput(
            token_id="BTC",
            label="BTC alert",
            groups=[],
        )

        async with _make_client(handler) as client:
            svc = SubscriptionService(client)
            await svc.create(input_data)

        assert "cooldownMinutes" not in captured_body

    @pytest.mark.asyncio
    async def test_update(self) -> None:
        """update() sends only non-None fields and returns a Subscription."""
        captured_body = None

        def handler(request: httpx.Request) -> httpx.Response:
            nonlocal captured_body
            assert request.method == "PUT"
            assert "/v1/subscriptions/sub_1" in str(request.url)
            captured_body = json.loads(request.content)
            return httpx.Response(200, json={
                "userId": "u1",
                "subId": "sub_1",
                "tokenId": "BTC",
                "label": "Updated label",
                "groups": [],
                "cooldownMinutes": 5,
                "bucketHash": "abc",
                "isActive": False,
                "createdAt": "2026-01-01T00:00:00Z",
                "updatedAt": "2026-03-01T00:00:00Z",
            })

        input_data = UpdateSubscriptionInput(
            label="Updated label",
            is_active=False,
        )

        async with _make_client(handler) as client:
            svc = SubscriptionService(client)
            result = await svc.update("sub_1", input_data)

        assert result.label == "Updated label"
        assert result.is_active is False
        assert captured_body == {"label": "Updated label", "isActive": False}

    @pytest.mark.asyncio
    async def test_delete(self) -> None:
        """delete() sends DELETE and returns None."""

        def handler(request: httpx.Request) -> httpx.Response:
            assert request.method == "DELETE"
            assert "/v1/subscriptions/sub_1" in str(request.url)
            return httpx.Response(204)

        async with _make_client(handler) as client:
            svc = SubscriptionService(client)
            result = await svc.delete("sub_1")

        assert result is None


# ── PaymentService ───────────────────────────────────────────────


class TestPaymentService:
    @pytest.mark.asyncio
    async def test_subscribe(self) -> None:
        """subscribe() sends correct body and returns SubscribeResponse."""
        captured_body = None

        def handler(request: httpx.Request) -> httpx.Response:
            nonlocal captured_body
            assert request.method == "POST"
            assert "/v1/payments/subscribe" in str(request.url)
            captured_body = json.loads(request.content)
            return httpx.Response(200, json={
                "tier": "pro",
                "billingCycle": "monthly",
                "price": 29.0,
                "currency": "USDC",
                "expiresAt": "2026-04-01T00:00:00Z",
                "payer": "0xABC",
                "mode": "live",
                "message": "Subscribed successfully",
            })

        input_data = SubscribeInput(tier="pro", billing_cycle="monthly", renew=False)

        async with _make_client(handler) as client:
            svc = PaymentService(client)
            result = await svc.subscribe(input_data)

        assert result.tier == "pro"
        assert result.price == 29.0
        assert result.currency == "USDC"
        assert captured_body == {"tier": "pro", "billingCycle": "monthly", "renew": False}

    @pytest.mark.asyncio
    async def test_status(self) -> None:
        """status() returns a BillingStatus."""

        def handler(request: httpx.Request) -> httpx.Response:
            assert request.method == "GET"
            assert "/v1/payments/status" in str(request.url)
            return httpx.Response(200, json={
                "tier": "basic",
                "tierName": "Basic",
                "billingCycle": "monthly",
                "maxSubs": 10,
                "apiAccess": True,
                "freeDataPushes": 50,
                "mode": "live",
                "expiresAt": "2026-04-01T00:00:00Z",
            })

        async with _make_client(handler) as client:
            svc = PaymentService(client)
            result = await svc.status()

        assert result.tier == "basic"
        assert result.tier_name == "Basic"
        assert result.api_access is True
        assert result.max_subs == 10

    @pytest.mark.asyncio
    async def test_upgrade_quote(self) -> None:
        """upgrade_quote() sends tier/cycle params and returns UpgradeQuote."""
        captured_url = None

        def handler(request: httpx.Request) -> httpx.Response:
            nonlocal captured_url
            captured_url = str(request.url)
            return httpx.Response(200, json={
                "currentTier": "basic",
                "currentCycle": "monthly",
                "currentExpiresAt": "2026-04-01T00:00:00Z",
                "targetTier": "pro",
                "targetCycle": "monthly",
                "basePrice": 29.0,
                "prorationCredit": 5.0,
                "finalPrice": 24.0,
                "currency": "USDC",
                "expiresAt": "2026-05-01T00:00:00Z",
            })

        async with _make_client(handler) as client:
            svc = PaymentService(client)
            result = await svc.upgrade_quote("pro", "monthly")

        assert result.target_tier == "pro"
        assert result.final_price == 24.0
        assert result.proration_credit == 5.0
        assert captured_url is not None
        assert "tier=pro" in captured_url
        assert "cycle=monthly" in captured_url


# ── WalletService ────────────────────────────────────────────────


class TestWalletService:
    @pytest.mark.asyncio
    async def test_register(self) -> None:
        """register() sends correct body and returns a Wallet."""
        captured_body = None

        def handler(request: httpx.Request) -> httpx.Response:
            nonlocal captured_body
            assert request.method == "POST"
            assert "/v1/wallets" in str(request.url)
            captured_body = json.loads(request.content)
            return httpx.Response(200, json={
                "userId": "u1",
                "walletAddress": "0xABC123",
                "chain": "base",
                "verifiedAt": "2026-03-01T00:00:00Z",
            })

        input_data = RegisterWalletInput(
            wallet_address="0xABC123",
            chain="base",
            signature="0xSIG",
            timestamp=1709000000,
        )

        async with _make_client(handler) as client:
            svc = WalletService(client)
            result = await svc.register(input_data)

        assert result.wallet_address == "0xABC123"
        assert result.chain == "base"
        assert captured_body["walletAddress"] == "0xABC123"
        assert captured_body["chain"] == "base"
        assert captured_body["signature"] == "0xSIG"
        assert captured_body["timestamp"] == 1709000000

    @pytest.mark.asyncio
    async def test_list(self) -> None:
        """list() returns a list of Wallet objects."""

        def handler(request: httpx.Request) -> httpx.Response:
            assert request.method == "GET"
            return httpx.Response(200, json={
                "wallets": [
                    {
                        "userId": "u1",
                        "walletAddress": "0xABC",
                        "chain": "base",
                        "verifiedAt": "2026-01-01T00:00:00Z",
                    },
                    {
                        "userId": "u1",
                        "walletAddress": "SOL123",
                        "chain": "solana",
                        "verifiedAt": "2026-02-01T00:00:00Z",
                    },
                ]
            })

        async with _make_client(handler) as client:
            svc = WalletService(client)
            result = await svc.list()

        assert len(result) == 2
        assert result[0].chain == "base"
        assert result[1].chain == "solana"

    @pytest.mark.asyncio
    async def test_remove(self) -> None:
        """remove() sends DELETE and returns None."""

        def handler(request: httpx.Request) -> httpx.Response:
            assert request.method == "DELETE"
            assert "/v1/wallets/0xABC" in str(request.url)
            return httpx.Response(204)

        async with _make_client(handler) as client:
            svc = WalletService(client)
            result = await svc.remove("0xABC")

        assert result is None


# ── ApiKeyService ────────────────────────────────────────────────


class TestApiKeyService:
    @pytest.mark.asyncio
    async def test_create(self) -> None:
        """create() sends name in body and returns ApiKeyCreateResponse."""
        captured_body = None

        def handler(request: httpx.Request) -> httpx.Response:
            nonlocal captured_body
            assert request.method == "POST"
            captured_body = json.loads(request.content)
            return httpx.Response(200, json={
                "keyId": "key_1",
                "name": "My Key",
                "prefix": "ak_live_",
                "key": "ak_live_full_secret_key",
                "createdAt": "2026-03-01T00:00:00Z",
            })

        async with _make_client(handler) as client:
            svc = ApiKeyService(client)
            result = await svc.create("My Key")

        assert result.key_id == "key_1"
        assert result.name == "My Key"
        assert result.key == "ak_live_full_secret_key"
        assert captured_body == {"name": "My Key"}

    @pytest.mark.asyncio
    async def test_list(self) -> None:
        """list() returns a list of ApiKeyListItem objects."""

        def handler(request: httpx.Request) -> httpx.Response:
            assert request.method == "GET"
            return httpx.Response(200, json={
                "keys": [
                    {
                        "keyId": "key_1",
                        "name": "My Key",
                        "prefix": "ak_live_",
                        "createdAt": "2026-03-01T00:00:00Z",
                    }
                ]
            })

        async with _make_client(handler) as client:
            svc = ApiKeyService(client)
            result = await svc.list()

        assert len(result) == 1
        assert result[0].key_id == "key_1"
        assert result[0].name == "My Key"

    @pytest.mark.asyncio
    async def test_revoke(self) -> None:
        """revoke() sends DELETE and returns None."""

        def handler(request: httpx.Request) -> httpx.Response:
            assert request.method == "DELETE"
            assert "/v1/api-keys/key_1" in str(request.url)
            return httpx.Response(204)

        async with _make_client(handler) as client:
            svc = ApiKeyService(client)
            result = await svc.revoke("key_1")

        assert result is None


# ── BundleService ────────────────────────────────────────────────


class TestBundleService:
    @pytest.mark.asyncio
    async def test_list(self) -> None:
        """list() returns a BundleListResponse with bundles and catalog."""

        def handler(request: httpx.Request) -> httpx.Response:
            assert request.method == "GET"
            return httpx.Response(200, json={
                "bundles": [
                    {
                        "bundleId": "bun_1",
                        "userId": "u1",
                        "walletAddress": "0xABC",
                        "bundleSize": 60,
                        "remaining": 45,
                        "purchasedAt": "2026-02-01T00:00:00Z",
                    }
                ],
                "catalog": [
                    {"name": "Starter", "pushes": 60, "price": 5.0},
                    {"name": "Pro", "pushes": 350, "price": 25.0},
                ],
                "perRequestPrice": 0.10,
            })

        async with _make_client(handler) as client:
            svc = BundleService(client)
            result = await svc.list()

        assert len(result.bundles) == 1
        assert result.bundles[0].bundle_id == "bun_1"
        assert result.bundles[0].remaining == 45
        assert len(result.catalog) == 2
        assert result.catalog[0].name == "Starter"
        assert result.per_request_price == 0.10

    @pytest.mark.asyncio
    async def test_purchase(self) -> None:
        """purchase() sends correct body and returns BundlePurchaseResponse."""
        captured_body = None

        def handler(request: httpx.Request) -> httpx.Response:
            nonlocal captured_body
            assert request.method == "POST"
            captured_body = json.loads(request.content)
            return httpx.Response(200, json={
                "bundleId": "bun_new",
                "userId": "u1",
                "walletAddress": "0xABC",
                "bundleName": "Starter",
                "totalPushes": 60,
                "remaining": 60,
                "price": 5.0,
                "purchasedAt": "2026-03-01T00:00:00Z",
                "payer": "0xABC",
                "transactionId": "tx_123",
            })

        input_data = PurchaseBundleInput(bundle_index=0, wallet_address="0xABC")

        async with _make_client(handler) as client:
            svc = BundleService(client)
            result = await svc.purchase(input_data)

        assert result.bundle_id == "bun_new"
        assert result.bundle_name == "Starter"
        assert result.total_pushes == 60
        assert result.transaction_id == "tx_123"
        assert captured_body == {"bundleIndex": 0, "walletAddress": "0xABC"}


# ── PushService ──────────────────────────────────────────────────


class TestPushService:
    @pytest.mark.asyncio
    async def test_list(self) -> None:
        """list() returns a list of PushSubscriptionResponse objects."""

        def handler(request: httpx.Request) -> httpx.Response:
            assert request.method == "GET"
            return httpx.Response(200, json={
                "subscriptions": [
                    {
                        "subscriptionId": "push_1",
                        "endpoint": "https://push.example.com/abc",
                        "createdAt": "2026-03-01T00:00:00Z",
                    }
                ]
            })

        async with _make_client(handler) as client:
            svc = PushService(client)
            result = await svc.list()

        assert len(result) == 1
        assert result[0].subscription_id == "push_1"
        assert result[0].endpoint == "https://push.example.com/abc"

    @pytest.mark.asyncio
    async def test_create(self) -> None:
        """create() sends correct body and returns PushSubscriptionResponse."""
        captured_body = None

        def handler(request: httpx.Request) -> httpx.Response:
            nonlocal captured_body
            assert request.method == "POST"
            captured_body = json.loads(request.content)
            return httpx.Response(200, json={
                "subscriptionId": "push_new",
                "endpoint": "https://push.example.com/xyz",
                "createdAt": "2026-03-01T00:00:00Z",
            })

        input_data = CreatePushInput(
            endpoint="https://push.example.com/xyz",
            keys=PushKeys(p256dh="p256dh_key_value", auth="auth_key_value"),
        )

        async with _make_client(handler) as client:
            svc = PushService(client)
            result = await svc.create(input_data)

        assert result.subscription_id == "push_new"
        assert result.endpoint == "https://push.example.com/xyz"
        assert captured_body == {
            "endpoint": "https://push.example.com/xyz",
            "keys": {
                "p256dh": "p256dh_key_value",
                "auth": "auth_key_value",
            },
        }

    @pytest.mark.asyncio
    async def test_delete(self) -> None:
        """delete() sends DELETE and returns None."""

        def handler(request: httpx.Request) -> httpx.Response:
            assert request.method == "DELETE"
            assert "/v1/push/subscriptions/push_1" in str(request.url)
            return httpx.Response(204)

        async with _make_client(handler) as client:
            svc = PushService(client)
            result = await svc.delete("push_1")

        assert result is None


# ── RedeemService ────────────────────────────────────────────────


class TestRedeemService:
    @pytest.mark.asyncio
    async def test_redeem(self) -> None:
        """redeem() sends code in body and returns RedeemResponse."""
        captured_body = None

        def handler(request: httpx.Request) -> httpx.Response:
            nonlocal captured_body
            assert request.method == "POST"
            assert "/v1/redeem" in str(request.url)
            captured_body = json.loads(request.content)
            return httpx.Response(200, json={
                "tier": "pro",
                "expiresAt": "2026-06-01T00:00:00Z",
                "message": "Code redeemed successfully",
            })

        async with _make_client(handler) as client:
            svc = RedeemService(client)
            result = await svc.redeem("PROMO_CODE_123")

        assert result.tier == "pro"
        assert result.expires_at == "2026-06-01T00:00:00Z"
        assert result.message == "Code redeemed successfully"
        assert captured_body == {"code": "PROMO_CODE_123"}
