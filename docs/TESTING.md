# Testing

## Test Discipline

Unit tests run on pytest + pytest-asyncio (`pip install -e ".[dev]"` for the
toolchain). CI (`ci.yml`) runs the unit suite on every push. Conformance
tests live in `tests/conformance/`, marked `-m conformance`, and replay
`attago-spec` fixtures against a live API — they never run in a plain unit
pass.

```bash
pytest                                   # unit suite
pytest -x                                # stop on first failure
pytest -k "test_name"                    # one test
pytest tests/conformance/ -m conformance # conformance (live API + spec dir)
```

## Runner & Baseline

- Runner: pytest (+ pytest-asyncio)
- Baseline test count: 176 (unit suite, 2026-07-31)

## Coverage Policy

Every service module has unit coverage on both the async and sync surfaces;
x402 auto-retry, webhook signature verification, and typed error paths are
covered explicitly. New surface lands with unit tests plus an `attago-spec`
fixture so conformance can assert it against the live API.
