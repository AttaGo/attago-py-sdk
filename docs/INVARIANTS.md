# Invariants

Rules that hold across all work. Append-only. Numbered `INVARIANT-NN`.

## Invariants

_(Add entries with `cz_add_invariant`.)_

### INVARIANT-01 — httpx is the ONLY runtime dependency — pyproject.toml never gains another; if httpx cannot do it, the feature is designed differently.
**Introduced by**: CLAUDE.md (Code Standards)
**Audience**: engineering

httpx is the ONLY runtime dependency — pyproject.toml never gains another; if httpx cannot do it, the feature is designed differently.

### INVARIANT-02 — Python 3.11+ floor; snake_case everywhere; type hints on all public methods (the package ships py.typed).
**Introduced by**: CLAUDE.md (Code Standards)
**Audience**: engineering

Python 3.11+ floor; snake_case everywhere; type hints on all public methods (the package ships py.typed).

### INVARIANT-03 — Incoming webhook payloads are authenticated ONLY by HMAC-SHA256 over the raw body against the X-AttaGo-Signature header (verify_signature); failed verification is a rejection.
**Introduced by**: README.md (Signature Verification)
**Audience**: engineering

Incoming webhook payloads are authenticated ONLY by HMAC-SHA256 over the raw body against the X-AttaGo-Signature header (verify_signature); failed verification is a rejection.
