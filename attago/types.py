"""Core types for the AttaGo Python SDK.

All response/request types as dataclasses, mirroring the Go SDK ``types.go``.
Uses ``@dataclass(slots=True)`` for memory efficiency and ``from_dict()``
classmethods for JSON hydration on complex response types.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol, Self, runtime_checkable

# ── Constants ───────────────────────────────────────────────────────

DEFAULT_BASE_URL = "https://api.attago.bid"
DEFAULT_COGNITO_REGION = "us-east-1"
VERSION = "0.1.0"

# ── x402 Signer ─────────────────────────────────────────────────────


@runtime_checkable
class X402Signer(Protocol):
    """x402 wallet signer for anonymous per-request payment.

    Implementations handle EVM (EIP-712) or Solana (ed25519) signing.
    """

    @property
    def address(self) -> str:
        """Wallet address (0x-prefixed EVM or base58 Solana)."""
        ...

    @property
    def network(self) -> str:
        """Network identifier (e.g. ``"eip155:8453"`` for Base)."""
        ...

    async def sign(self, requirements: X402PaymentRequirements) -> str:
        """Sign an x402 payment payload, returning a base64-encoded payment string."""
        ...


# ── x402 types ──────────────────────────────────────────────────────


@dataclass(slots=True)
class X402Resource:
    """Describes the protected resource."""

    url: str
    description: str
    mime_type: str

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        return cls(
            url=data["url"],
            description=data["description"],
            mime_type=data.get("mimeType", ""),
        )


@dataclass(slots=True)
class X402AcceptedPayment:
    """One accepted payment option from x402 requirements."""

    scheme: str
    network: str
    amount: str
    asset: str
    pay_to: str
    max_timeout_seconds: int
    extra: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        return cls(
            scheme=data["scheme"],
            network=data["network"],
            amount=data["amount"],
            asset=data["asset"],
            pay_to=data["payTo"],
            max_timeout_seconds=data.get("maxTimeoutSeconds", 0),
            extra=data.get("extra", {}),
        )


@dataclass(slots=True)
class X402PaymentRequirements:
    """Decoded x402 payment requirements from the PAYMENT-REQUIRED header."""

    x402_version: int
    resource: X402Resource
    accepts: list[X402AcceptedPayment]

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        return cls(
            x402_version=data["x402Version"],
            resource=X402Resource.from_dict(data["resource"]),
            accepts=[X402AcceptedPayment.from_dict(a) for a in data.get("accepts", [])],
        )


# ── Auth types ──────────────────────────────────────────────────────


@dataclass(slots=True)
class CognitoTokens:
    """Cognito token set for persistence/restoration."""

    id_token: str
    access_token: str
    refresh_token: str

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        return cls(
            id_token=data["idToken"],
            access_token=data["accessToken"],
            refresh_token=data["refreshToken"],
        )


@dataclass(slots=True)
class SignUpInput:
    """Parameters for account registration."""

    email: str
    password: str
    cognito_client_id: str
    cognito_region: str = DEFAULT_COGNITO_REGION


@dataclass(slots=True)
class ConfirmSignUpInput:
    """Parameters for confirming a new account."""

    email: str
    code: str
    cognito_client_id: str
    cognito_region: str = DEFAULT_COGNITO_REGION


@dataclass(slots=True)
class ForgotPasswordInput:
    """Parameters for triggering a password reset."""

    email: str
    cognito_client_id: str
    cognito_region: str = DEFAULT_COGNITO_REGION


@dataclass(slots=True)
class ConfirmForgotPasswordInput:
    """Parameters for completing a password reset."""

    email: str
    code: str
    new_password: str
    cognito_client_id: str
    cognito_region: str = DEFAULT_COGNITO_REGION


# ── Agent types ─────────────────────────────────────────────────────


@dataclass(slots=True)
class CompositeScore:
    """Top-level Go/No-Go signal summary."""

    score: float
    signal: str  # "GO", "NO-GO", "NEUTRAL"
    confidence: float

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        return cls(
            score=float(data["score"]),
            signal=data["signal"],
            confidence=float(data["confidence"]),
        )


@dataclass(slots=True)
class AgentScoreResponse:
    """Response from GET /v1/agent/score."""

    token: str
    composite: CompositeScore
    spot: dict[str, Any]
    perps: dict[str, Any] | None
    context: dict[str, Any]
    market: dict[str, Any]
    deriv_symbols: list[str]
    has_derivatives: bool
    sources: list[dict[str, Any]]
    meta: dict[str, Any]
    request_id: str | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        return cls(
            token=data["token"],
            composite=CompositeScore.from_dict(data["composite"]),
            spot=data.get("spot", {}),
            perps=data.get("perps"),
            context=data.get("context", {}),
            market=data.get("market", {}),
            deriv_symbols=data.get("derivSymbols", []),
            has_derivatives=data.get("hasDerivatives", False),
            sources=data.get("sources", []),
            meta=data.get("meta", {}),
            request_id=data.get("requestId"),
        )


@dataclass(slots=True)
class AgentDataResponse:
    """Response from GET /v1/agent/data."""

    assets: dict[str, dict[str, Any]]
    asset_order: list[str]
    market: dict[str, Any]
    sources: list[dict[str, Any]]
    meta: dict[str, Any]
    request_id: str | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        return cls(
            assets=data.get("assets", {}),
            asset_order=data.get("assetOrder", []),
            market=data.get("market", {}),
            sources=data.get("sources", []),
            meta=data.get("meta", {}),
            request_id=data.get("requestId"),
        )


# ── Data types ──────────────────────────────────────────────────────


@dataclass(slots=True)
class BundleUsage:
    """Bundle credit consumption in a data-push response."""

    bundle_id: str
    remaining: int

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        return cls(
            bundle_id=data["bundleId"],
            remaining=int(data["remaining"]),
        )


@dataclass(slots=True)
class PushUsage:
    """Included push consumption in a data-push response."""

    used: int
    total: int
    remaining: int

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        return cls(
            used=int(data["used"]),
            total=int(data["total"]),
            remaining=int(data["remaining"]),
        )


@dataclass(slots=True)
class DataLatestResponse:
    """Response from GET /v1/data/latest."""

    assets: dict[str, dict[str, Any]]
    asset_order: list[str]
    market: dict[str, Any]
    sources: list[dict[str, Any]]
    meta: dict[str, Any]

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        return cls(
            assets=data.get("assets", {}),
            asset_order=data.get("assetOrder", []),
            market=data.get("market", {}),
            sources=data.get("sources", []),
            meta=data.get("meta", {}),
        )


@dataclass(slots=True)
class DataTokenResponse:
    """Response from GET /v1/api/data/{token}."""

    token: str
    composite: dict[str, Any]
    spot: dict[str, Any]
    perps: dict[str, Any] | None
    context: dict[str, Any]
    market: dict[str, Any]
    deriv_symbols: list[str]
    has_derivatives: bool
    sources: list[dict[str, Any]]
    meta: dict[str, Any]
    request_id: str
    mode: str
    bundle: BundleUsage | None = None
    included_push: PushUsage | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        bundle_raw = data.get("bundle")
        push_raw = data.get("includedPush")
        return cls(
            token=data["token"],
            composite=data.get("composite", {}),
            spot=data.get("spot", {}),
            perps=data.get("perps"),
            context=data.get("context", {}),
            market=data.get("market", {}),
            deriv_symbols=data.get("derivSymbols", []),
            has_derivatives=data.get("hasDerivatives", False),
            sources=data.get("sources", []),
            meta=data.get("meta", {}),
            request_id=data["requestId"],
            mode=data.get("mode", ""),
            bundle=BundleUsage.from_dict(bundle_raw) if bundle_raw else None,
            included_push=PushUsage.from_dict(push_raw) if push_raw else None,
        )


@dataclass(slots=True)
class DataPushResponse:
    """Response from GET /v1/data/push/{requestId}."""

    request_id: str
    token_id: str
    created_at: str
    data: dict[str, Any]

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        return cls(
            request_id=data["requestId"],
            token_id=data["tokenId"],
            created_at=data["createdAt"],
            data=data.get("data", {}),
        )


# ── Subscription types ──────────────────────────────────────────────


@dataclass(slots=True)
class SubscriptionCondition:
    """A single alert condition (metric + operator + threshold)."""

    metric_name: str
    threshold_op: str  # "gt", "lt", "gte", "lte", "eq"
    threshold_val: Any  # number or string

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        return cls(
            metric_name=data["metricName"],
            threshold_op=data["thresholdOp"],
            threshold_val=data["thresholdVal"],
        )


@dataclass(slots=True)
class Subscription:
    """An alert subscription returned by the API."""

    user_id: str
    sub_id: str
    token_id: str
    label: str
    groups: list[list[SubscriptionCondition]]  # OR-of-ANDs
    cooldown_minutes: int
    bucket_hash: str
    is_active: bool
    created_at: str
    updated_at: str
    active_token_shard: str | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        groups = [
            [SubscriptionCondition.from_dict(c) for c in group]
            for group in data.get("groups", [])
        ]
        return cls(
            user_id=data["userId"],
            sub_id=data["subId"],
            token_id=data["tokenId"],
            label=data.get("label", ""),
            groups=groups,
            cooldown_minutes=data.get("cooldownMinutes", 5),
            bucket_hash=data.get("bucketHash", ""),
            is_active=data.get("isActive", True),
            created_at=data.get("createdAt", ""),
            updated_at=data.get("updatedAt", ""),
            active_token_shard=data.get("activeTokenShard"),
        )


@dataclass(slots=True)
class CatalogMetric:
    """A metric definition from the subscription catalog."""

    label: str
    type: str  # "number" or "enum"
    operators: list[str]
    unit: str | None = None
    min: float | None = None
    max: float | None = None
    values: list[str] | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        return cls(
            label=data["label"],
            type=data["type"],
            operators=data.get("operators", []),
            unit=data.get("unit"),
            min=data.get("min"),
            max=data.get("max"),
            values=data.get("values"),
        )


@dataclass(slots=True)
class CatalogResponse:
    """Response from GET /v1/subscriptions/catalog."""

    tokens: list[str]
    metrics: dict[str, CatalogMetric]
    tier: str
    max_subscriptions: int
    mode: str

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        metrics = {
            k: CatalogMetric.from_dict(v) for k, v in data.get("metrics", {}).items()
        }
        return cls(
            tokens=data.get("tokens", []),
            metrics=metrics,
            tier=data.get("tier", ""),
            max_subscriptions=data.get("maxSubscriptions", 0),
            mode=data.get("mode", ""),
        )


@dataclass(slots=True)
class CreateSubscriptionInput:
    """Parameters for creating an alert subscription."""

    token_id: str
    label: str
    groups: list[list[SubscriptionCondition]]
    cooldown_minutes: int | None = None  # defaults to 5 server-side


@dataclass(slots=True)
class UpdateSubscriptionInput:
    """Parameters for updating a subscription. All fields are optional."""

    label: str | None = None
    groups: list[list[SubscriptionCondition]] | None = None
    cooldown_minutes: int | None = None
    is_active: bool | None = None


# ── Payment types ───────────────────────────────────────────────────


@dataclass(slots=True)
class SubscribeInput:
    """Parameters for subscribing to a billing tier."""

    tier: str  # "basic", "pro", "business"
    billing_cycle: str  # "monthly", "yearly"
    renew: bool = False


@dataclass(slots=True)
class SubscribeResponse:
    """Response from a successful subscription."""

    tier: str
    billing_cycle: str
    price: float
    currency: str
    expires_at: str
    payer: str
    mode: str
    message: str

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        return cls(
            tier=data["tier"],
            billing_cycle=data["billingCycle"],
            price=float(data["price"]),
            currency=data["currency"],
            expires_at=data["expiresAt"],
            payer=data["payer"],
            mode=data.get("mode", ""),
            message=data.get("message", ""),
        )


@dataclass(slots=True)
class IncludedPushes:
    """Push usage within a billing period."""

    total: int
    used: int
    remaining: int
    period_start: str
    period_end: str

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        return cls(
            total=int(data["total"]),
            used=int(data["used"]),
            remaining=int(data["remaining"]),
            period_start=data["periodStart"],
            period_end=data["periodEnd"],
        )


@dataclass(slots=True)
class BillingStatus:
    """Current billing/tier status."""

    tier: str
    tier_name: str
    billing_cycle: str
    max_subs: int
    api_access: bool
    free_data_pushes: int
    mode: str
    expires_at: str | None = None
    included_pushes: IncludedPushes | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        pushes_raw = data.get("includedPushes")
        return cls(
            tier=data["tier"],
            tier_name=data["tierName"],
            billing_cycle=data.get("billingCycle", ""),
            max_subs=data.get("maxSubs", 0),
            api_access=data.get("apiAccess", False),
            free_data_pushes=data.get("freeDataPushes", 0),
            mode=data.get("mode", ""),
            expires_at=data.get("expiresAt"),
            included_pushes=IncludedPushes.from_dict(pushes_raw) if pushes_raw else None,
        )


@dataclass(slots=True)
class UpgradeQuote:
    """Pro-rated upgrade price quote."""

    current_tier: str
    current_cycle: str
    current_expires_at: str
    target_tier: str
    target_cycle: str
    base_price: float
    proration_credit: float
    final_price: float
    currency: str
    expires_at: str

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        return cls(
            current_tier=data["currentTier"],
            current_cycle=data["currentCycle"],
            current_expires_at=data["currentExpiresAt"],
            target_tier=data["targetTier"],
            target_cycle=data["targetCycle"],
            base_price=float(data["basePrice"]),
            proration_credit=float(data["prorationCredit"]),
            final_price=float(data["finalPrice"]),
            currency=data["currency"],
            expires_at=data["expiresAt"],
        )


# ── Wallet types ────────────────────────────────────────────────────


@dataclass(slots=True)
class RegisterWalletInput:
    """Parameters for registering a wallet."""

    wallet_address: str
    chain: str  # "base", "avax", "polygon", "arbitrum", "optimism", "solana"
    signature: str
    timestamp: int  # Unix seconds


@dataclass(slots=True)
class Wallet:
    """A verified wallet returned by the API."""

    user_id: str
    wallet_address: str
    chain: str
    verified_at: str

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        return cls(
            user_id=data["userId"],
            wallet_address=data["walletAddress"],
            chain=data["chain"],
            verified_at=data["verifiedAt"],
        )


# ── Webhook types ───────────────────────────────────────────────────


@dataclass(slots=True)
class WebhookCreateResponse:
    """Returned on webhook creation (includes secret -- shown only once)."""

    webhook_id: str
    url: str
    secret: str
    created_at: str

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        return cls(
            webhook_id=data["webhookId"],
            url=data["url"],
            secret=data["secret"],
            created_at=data["createdAt"],
        )


@dataclass(slots=True)
class WebhookListItem:
    """A webhook in a list response (secret stripped)."""

    webhook_id: str
    url: str
    created_at: str

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        return cls(
            webhook_id=data["webhookId"],
            url=data["url"],
            created_at=data["createdAt"],
        )


@dataclass(slots=True)
class WebhookTestResult:
    """Result of a test delivery (SDK-side or server-side)."""

    success: bool
    attempts: int
    status_code: int | None = None
    error: str | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        return cls(
            success=data["success"],
            attempts=data.get("attempts", 0),
            status_code=data.get("statusCode"),
            error=data.get("error"),
        )


@dataclass(slots=True)
class SendTestOptions:
    """Configures SDK-side webhook test delivery."""

    url: str
    secret: str
    token: str = "BTC"
    state: str = "triggered"
    environment: str = "production"
    backoff_ms: list[int] | None = None  # default: [1000, 4000, 16000]


@dataclass(slots=True)
class WebhookPayloadAlert:
    """Alert section of a webhook payload."""

    id: str
    label: str
    token: str
    state: str  # "triggered" or "resolved"

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        return cls(
            id=data["id"],
            label=data["label"],
            token=data["token"],
            state=data["state"],
        )


@dataclass(slots=True)
class WebhookPayloadData:
    """Data section of a webhook payload."""

    url: str | None = None
    expires_at: str | None = None
    fallback_url: str | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        return cls(
            url=data.get("url"),
            expires_at=data.get("expiresAt"),
            fallback_url=data.get("fallbackUrl"),
        )


@dataclass(slots=True)
class WebhookPayload:
    """v2 webhook delivery payload (alert or test)."""

    event: str  # "alert" or "test"
    version: str
    environment: str
    alert: WebhookPayloadAlert
    data: WebhookPayloadData
    timestamp: str

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        return cls(
            event=data["event"],
            version=data["version"],
            environment=data["environment"],
            alert=WebhookPayloadAlert.from_dict(data["alert"]),
            data=WebhookPayloadData.from_dict(data["data"]),
            timestamp=data["timestamp"],
        )


# ── API Key types ───────────────────────────────────────────────────


@dataclass(slots=True)
class ApiKeyCreateResponse:
    """Returned on API key creation (includes raw key -- shown only once)."""

    key_id: str
    name: str
    prefix: str
    key: str  # full raw key, shown only once
    created_at: str

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        return cls(
            key_id=data["keyId"],
            name=data["name"],
            prefix=data["prefix"],
            key=data["key"],
            created_at=data["createdAt"],
        )


@dataclass(slots=True)
class ApiKeyListItem:
    """An API key in a list response (raw key never shown)."""

    key_id: str
    name: str
    prefix: str
    created_at: str
    last_used_at: str | None = None
    revoked_at: str | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        return cls(
            key_id=data["keyId"],
            name=data["name"],
            prefix=data["prefix"],
            created_at=data["createdAt"],
            last_used_at=data.get("lastUsedAt"),
            revoked_at=data.get("revokedAt"),
        )


# ── Bundle types ────────────────────────────────────────────────────


@dataclass(slots=True)
class Bundle:
    """A purchased data-push credit bundle."""

    bundle_id: str
    user_id: str
    wallet_address: str
    bundle_size: int
    remaining: int
    purchased_at: str
    expires_at: str | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        return cls(
            bundle_id=data["bundleId"],
            user_id=data["userId"],
            wallet_address=data["walletAddress"],
            bundle_size=int(data["bundleSize"]),
            remaining=int(data["remaining"]),
            purchased_at=data["purchasedAt"],
            expires_at=data.get("expiresAt"),
        )


@dataclass(slots=True)
class BundleCatalogEntry:
    """An available bundle package."""

    name: str
    pushes: int
    price: float

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        return cls(
            name=data["name"],
            pushes=int(data["pushes"]),
            price=float(data["price"]),
        )


@dataclass(slots=True)
class BundleListResponse:
    """Response from listing bundles."""

    bundles: list[Bundle]
    catalog: list[BundleCatalogEntry]
    per_request_price: float

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        return cls(
            bundles=[Bundle.from_dict(b) for b in data.get("bundles", [])],
            catalog=[BundleCatalogEntry.from_dict(c) for c in data.get("catalog", [])],
            per_request_price=float(data.get("perRequestPrice", 0)),
        )


@dataclass(slots=True)
class PurchaseBundleInput:
    """Parameters for purchasing a bundle."""

    bundle_index: int
    wallet_address: str


@dataclass(slots=True)
class BundlePurchaseResponse:
    """Response from a successful bundle purchase."""

    bundle_id: str
    user_id: str
    wallet_address: str
    bundle_name: str
    total_pushes: int
    remaining: int
    price: float
    purchased_at: str
    payer: str
    transaction_id: str

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        return cls(
            bundle_id=data["bundleId"],
            user_id=data["userId"],
            wallet_address=data["walletAddress"],
            bundle_name=data["bundleName"],
            total_pushes=int(data["totalPushes"]),
            remaining=int(data["remaining"]),
            price=float(data["price"]),
            purchased_at=data["purchasedAt"],
            payer=data["payer"],
            transaction_id=data["transactionId"],
        )


# ── Push types ──────────────────────────────────────────────────────


@dataclass(slots=True)
class PushKeys:
    """Web Push subscription encryption keys."""

    p256dh: str
    auth: str

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        return cls(
            p256dh=data["p256dh"],
            auth=data["auth"],
        )


@dataclass(slots=True)
class CreatePushInput:
    """Parameters for registering a push subscription."""

    endpoint: str
    keys: PushKeys


@dataclass(slots=True)
class PushSubscriptionResponse:
    """A push subscription returned by the API."""

    subscription_id: str
    endpoint: str
    created_at: str

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        return cls(
            subscription_id=data["subscriptionId"],
            endpoint=data["endpoint"],
            created_at=data["createdAt"],
        )


# ── Redeem types ────────────────────────────────────────────────────


@dataclass(slots=True)
class RedeemResponse:
    """Response from a successful code redemption."""

    tier: str
    expires_at: str
    message: str

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        return cls(
            tier=data["tier"],
            expires_at=data["expiresAt"],
            message=data["message"],
        )


# ── MCP types ───────────────────────────────────────────────────────


@dataclass(slots=True)
class McpToolsCapability:
    """Describes the tools capability."""

    list_changed: bool = False

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        return cls(list_changed=data.get("listChanged", False))


@dataclass(slots=True)
class McpCapabilities:
    """Describes server capabilities."""

    tools: McpToolsCapability | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        tools_raw = data.get("tools")
        return cls(
            tools=McpToolsCapability.from_dict(tools_raw) if tools_raw else None,
        )


@dataclass(slots=True)
class McpServerMetadata:
    """Server identity info."""

    name: str
    version: str

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        return cls(name=data["name"], version=data["version"])


@dataclass(slots=True)
class McpServerInfo:
    """Response from MCP initialize."""

    protocol_version: str
    capabilities: McpCapabilities
    server_info: McpServerMetadata
    instructions: str | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        return cls(
            protocol_version=data["protocolVersion"],
            capabilities=McpCapabilities.from_dict(data.get("capabilities", {})),
            server_info=McpServerMetadata.from_dict(data["serverInfo"]),
            instructions=data.get("instructions"),
        )


@dataclass(slots=True)
class McpTool:
    """A tool definition from tools/list."""

    name: str
    description: str
    input_schema: dict[str, Any]
    annotations: dict[str, Any] | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        return cls(
            name=data["name"],
            description=data["description"],
            input_schema=data.get("inputSchema", {}),
            annotations=data.get("annotations"),
        )


@dataclass(slots=True)
class McpToolContent:
    """A content item in a tool result."""

    type: str  # "text", "image", "resource"
    text: str | None = None
    data: str | None = None
    mime_type: str | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        return cls(
            type=data["type"],
            text=data.get("text"),
            data=data.get("data"),
            mime_type=data.get("mimeType"),
        )


@dataclass(slots=True)
class McpToolCallResult:
    """Result of calling an MCP tool."""

    content: list[McpToolContent]
    is_error: bool = False

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        return cls(
            content=[McpToolContent.from_dict(c) for c in data.get("content", [])],
            is_error=data.get("isError", False),
        )


# ── User profile types ──────────────────────────────────────────────


@dataclass(slots=True)
class UserProfile:
    """Response from GET /v1/user/profile."""

    user_id: str
    email: str
    plan_tier: str
    role: str
    effective_tier: str
    delivery_preference: str
    created_at: str
    updated_at: str
    tier_override: str | None = None
    arena_username: str | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        return cls(
            user_id=data["userId"],
            email=data["email"],
            plan_tier=data.get("planTier", "free"),
            role=data.get("role", "user"),
            effective_tier=data.get("effectiveTier", "free"),
            delivery_preference=data.get("deliveryPreference", "email"),
            created_at=data.get("createdAt", ""),
            updated_at=data.get("updatedAt", ""),
            tier_override=data.get("tierOverride"),
            arena_username=data.get("arenaUsername"),
        )
