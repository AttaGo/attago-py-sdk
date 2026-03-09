"""AttaGo Python SDK — async/sync client for the AttaGo crypto trading dashboard API.

Three authentication modes:

- **API key**: ``AttaGoClient(api_key="ak_live_...")``
- **x402 signer**: ``AttaGoClient(signer=my_signer)``
- **Cognito**: ``AttaGoClient(email="...", password="...", cognito_client_id="...")``

Example::

    from attago import AttaGoClient

    async with AttaGoClient(api_key="ak_live_abc123") as client:
        score = await client.agent.get_score("BTC")
        print(score.composite.signal)  # "GO" | "NO-GO" | "NEUTRAL"
"""

__version__ = "0.1.0"

# ── Core ──
from attago.client import AttaGoClient
from attago.auth import CognitoAuth

# ── Errors ──
from attago.errors import (
    AttaGoError,
    ApiError,
    PaymentRequiredError,
    RateLimitError,
    AuthError,
    MfaRequiredError,
    McpError,
)

# ── Services ──
from attago.agent import AgentService
from attago.data import DataService
from attago.subscriptions import SubscriptionService
from attago.payments import PaymentService
from attago.wallets import WalletService
from attago.webhooks import WebhookService, build_test_payload, sign_payload, verify_signature
from attago.mcp import McpService
from attago.api_keys import ApiKeyService
from attago.bundles import BundleService
from attago.push import PushService
from attago.redeem import RedeemService
from attago.listener import WebhookListener

# ── x402 ──
from attago.x402 import parse_payment_required, filter_accepts_by_network

# ── Types (re-export everything) ──
from attago.types import (
    DEFAULT_BASE_URL,
    DEFAULT_COGNITO_REGION,
    VERSION,
    X402Signer,
    X402Resource,
    X402AcceptedPayment,
    X402PaymentRequirements,
    CognitoTokens,
    SignUpInput,
    ConfirmSignUpInput,
    ForgotPasswordInput,
    ConfirmForgotPasswordInput,
    CompositeScore,
    AgentScoreResponse,
    AgentDataResponse,
    BundleUsage,
    PushUsage,
    DataLatestResponse,
    DataTokenResponse,
    DataPushResponse,
    SubscriptionCondition,
    Subscription,
    CatalogMetric,
    CatalogResponse,
    CreateSubscriptionInput,
    UpdateSubscriptionInput,
    SubscribeInput,
    SubscribeResponse,
    IncludedPushes,
    BillingStatus,
    UpgradeQuote,
    RegisterWalletInput,
    Wallet,
    WebhookCreateResponse,
    WebhookListItem,
    WebhookTestResult,
    SendTestOptions,
    WebhookPayloadAlert,
    WebhookPayloadData,
    WebhookPayload,
    ApiKeyCreateResponse,
    ApiKeyListItem,
    Bundle,
    BundleCatalogEntry,
    BundleListResponse,
    PurchaseBundleInput,
    BundlePurchaseResponse,
    PushKeys,
    CreatePushInput,
    PushSubscriptionResponse,
    RedeemResponse,
    McpToolsCapability,
    McpCapabilities,
    McpServerMetadata,
    McpServerInfo,
    McpTool,
    McpToolContent,
    McpToolCallResult,
    UserProfile,
)

__all__ = [
    # Version
    "__version__",
    # Core
    "AttaGoClient",
    "CognitoAuth",
    # Errors
    "AttaGoError",
    "ApiError",
    "PaymentRequiredError",
    "RateLimitError",
    "AuthError",
    "MfaRequiredError",
    "McpError",
    # Services
    "AgentService",
    "DataService",
    "SubscriptionService",
    "PaymentService",
    "WalletService",
    "WebhookService",
    "McpService",
    "ApiKeyService",
    "BundleService",
    "PushService",
    "RedeemService",
    "WebhookListener",
    # Webhook helpers
    "build_test_payload",
    "sign_payload",
    "verify_signature",
    # x402 helpers
    "parse_payment_required",
    "filter_accepts_by_network",
]
