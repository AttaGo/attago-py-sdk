# Architecture

Subsystems, capabilities, and components. Tracked entities live in
`docs/subsystems/` and `docs/features/` with frontmatter that declares the
Project DAG; this doc is the prose overview.

## Subsystems

Flat package `attago/`, module per concern (mirroring the js-sdk layout):

- **Client core** (`client.py`) — `AttaGoClient`: async context manager,
  `sync=True` opt-in. Three mutually exclusive auth modes: `api_key`,
  `signer` (x402), `email`/`password`/`cognito_client_id` (Cognito).
  Service attributes, one module each: `agent`, `data`, `subscriptions`,
  `payments`, `wallets`, `webhooks`, `mcp`, `api_keys`, `bundles`, `push`,
  `redeem`.
- **Types** (`types.py`) — plain typed dataclasses (no Pydantic); package
  ships `py.typed` (PEP 561).
- **Errors** (`errors.py`) — `ApiError`, `PaymentRequiredError` (402),
  `RateLimitError` (429), raised as typed exceptions.
- **x402** (`x402.py`) — signer abstraction; 402 responses are auto-signed
  and retried.
- **Auth** (`auth.py`) — Cognito sign-in / token refresh.
- **Webhooks** (`webhooks.py`, `listener.py`) — CRUD + test delivery,
  HMAC-SHA256 `verify_signature` over the raw body against
  `X-AttaGo-Signature`, and `WebhookListener` (on_alert/on_test callbacks).
- **MCP** (`mcp.py`) — JSON-RPC 2.0 client: initialize, list_tools,
  call_tool, ping.

HTTP is carried by **httpx** — the single runtime dependency, chosen for
first-class async support.

## Capabilities

- **Conformance**: `pytest tests/conformance/ -m conformance` replays
  `attago-spec` fixtures against a live API (`ATTAGO_BASE_URL`,
  `ATTAGO_API_KEY`, `ATTAGO_SPEC_DIR`); runs in this repo's CI and in the
  spec repo's weekly matrix.
- **Reference lineage**: `attago-js-sdk` is the reference implementation;
  origin plan `attago` repo, `docs/plans/2026-03-07-sdk-plan.md`.
