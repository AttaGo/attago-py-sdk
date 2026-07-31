# Decisions

Project-wide architectural decision records (ADRs). Append-only. Numbered `D-NNN`.
Each entry carries a `**Status**` (`active` | `superseded` | `deprecated`). When a
decision supersedes another, the predecessor stays in the record — annotated in place
with a `**Superseded by**: D-NNN` back-ref and `**Status**: superseded` — so the
lifecycle is navigable and the current decision is the one that surfaces.

## Decisions

_(Add entries with `cz_add_decision`.)_

### D-001 — Async-first with explicit sync opt-in, carried by httpx — the one runtime dependency

**Context**: Python consumers split between asyncio services and simple scripts; the SDK family's zero-dependency rule meets Python's stdlib having no mature async HTTP client.
**Decision**: The native surface is async (async with AttaGoClient); sync is opt-in (sync=True, *_sync methods). httpx is the single runtime dependency; nothing else is added.
**Consequences**: One deliberate exception to the family zero-dep rule, isolated to HTTP transport; async and sync stay one codebase rather than two.
**Evidence**: CLAUDE.md (Code Standards: 'httpx for HTTP (async default, sync opt-in)', 'One runtime dep: httpx'); README.md (Quick Start, Sync Mode)
**Status**: active (2026-07-31)

### D-002 — dataclasses for response types, not Pydantic; ship py.typed

**Context**: Response models need typing without imposing a heavy validation framework on consumers.
**Decision**: Plain typed dataclasses everywhere; the package ships py.typed (PEP 561) so type checkers see the full surface. Validation authority stays with the attago-spec schemas.
**Consequences**: No Pydantic in the dependency tree; wire validation is conformance's job, not the model layer's.
**Evidence**: CLAUDE.md (Code Standards: 'dataclasses for response types (no Pydantic)'); attago/py.typed
**Status**: active (2026-07-31)

### D-003 — Three mutually exclusive auth modes on one client

**Context**: The API serves keyed scripts, anonymous x402 wallet agents, and Cognito account holders.
**Decision**: AttaGoClient accepts exactly one of api_key, signer, or email+password+cognito_client_id.
**Consequences**: Auth intent explicit per instance; dual-mode callers hold two clients.
**Evidence**: README.md (Quick Start); CLAUDE.md
**Status**: active (2026-07-31)
