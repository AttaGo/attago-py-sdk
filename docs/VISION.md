# Vision

## What & Why

The Python SDK for the AttaGo crypto trading dashboard API (`pip install
attago`) — one of four hand-written, idiomatic clients (TypeScript, Python,
Go, Ruby). It gives Python agents, notebooks, and services the full API
surface — Go/No-Go scores, market data, alert subscriptions, payments,
wallets, webhooks, and the MCP JSON-RPC surface — through an async-first
client (`async with AttaGoClient(...)`) with an explicit sync opt-in
(`sync=True`, `*_sync` methods).

Correctness is guaranteed externally: the `attago-spec` repo holds the
conformance contract, and this SDK's conformance suite runs against the
live API in its own CI and in the spec repo's weekly matrix.

## Differentiation

- **Async-first, sync available**: asyncio is the native mode; the sync
  surface is generated opt-in, not a parallel codebase.
- **One deliberate dependency**: httpx — the family's zero-dependency rule
  is traded here for a mature async HTTP client; nothing else gets in.
- **dataclasses, not Pydantic**: response types are plain typed dataclasses;
  the SDK ships `py.typed` (PEP 561) so consumers get full type checking.

## Scope Boundaries

- Not the API: the backend lives in the `attago` repo.
- Not the contract: schemas and fixtures live in `attago-spec`.
- Not the reference implementation: `attago-js-sdk` holds that role; this
  repo translates its surface into Python idiom.
