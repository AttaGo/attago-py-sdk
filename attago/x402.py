"""x402 payment protocol helpers.

Mirrors the Go SDK's ``x402.go``:
- Parse the base64-encoded ``Payment-Required`` header
- Find accepted payment matching a signer's network
- Wrap a request with automatic 402 sign-and-retry
"""

from __future__ import annotations

import base64
import json
from typing import Any

import httpx

from .errors import PaymentRequiredError


# ── Header Parsing ───────────────────────────────────────────────────


def parse_payment_required(headers: dict[str, str] | httpx.Headers) -> dict[str, Any] | None:
    """Decode the base64-encoded ``Payment-Required`` header.

    Tries standard base64 first, then URL-safe base64.
    Returns ``None`` if the header is missing or unparseable.
    """
    raw = headers.get("payment-required") or headers.get("Payment-Required")
    if not raw:
        return None
    try:
        return json.loads(base64.b64decode(raw))
    except Exception:
        try:
            return json.loads(base64.urlsafe_b64decode(raw))
        except Exception:
            return None


# ── Network Filtering ────────────────────────────────────────────────


def filter_accepts_by_network(accepts: list[dict[str, Any]], network: str) -> dict[str, Any] | None:
    """Find the first accepted payment option matching *network*.

    Returns ``None`` if no match is found.
    """
    for a in accepts:
        if a.get("network") == network:
            return a
    return None


# ── x402 Auto-Retry ─────────────────────────────────────────────────


async def do_with_x402(
    client: httpx.AsyncClient,
    signer: Any,
    method: str,
    url: str,
    *,
    headers: dict[str, str] | None = None,
    content: bytes | None = None,
    json_body: Any | None = None,
) -> httpx.Response:
    """Send *method* request to *url*; on 402, sign and retry.

    This mirrors the Go SDK's ``doWithX402`` function:

    1. Fire the original request.
    2. If the response is **not** 402, return it immediately.
    3. On 402: parse ``Payment-Required``, find the accepted option
       matching ``signer.network()``, call ``signer.sign()``, and retry
       with the ``Payment-Signature`` header added.
    4. If the retry is also 402, raise :class:`PaymentRequiredError`.
    """
    # ── First attempt ──
    response = await client.request(
        method, url, headers=headers, content=content,
    )

    if response.status_code != 402:
        return response

    # ── Parse 402 ──
    requirements = parse_payment_required(response.headers)
    if requirements is None:
        raise PaymentRequiredError(
            message="Payment required (unparseable requirements)",
            headers=dict(response.headers),
        )

    # ── Find matching network ──
    accepts = requirements.get("accepts", [])
    accepted = filter_accepts_by_network(accepts, signer.network())
    if accepted is None:
        raise PaymentRequiredError(
            message=f"No accepted payment for network {signer.network()!r}",
            payment_requirements=requirements,
            headers=dict(response.headers),
        )

    # ── Sign payment ──
    try:
        signature = await signer.sign(requirements)
    except Exception as exc:
        raise PaymentRequiredError(
            message=f"x402 signing failed: {exc}",
            payment_requirements=requirements,
        ) from exc

    # ── Retry with signature ──
    retry_headers = dict(headers or {})
    retry_headers["Payment-Signature"] = signature

    retry_response = await client.request(
        method, url, headers=retry_headers, content=content,
    )

    if retry_response.status_code == 402:
        raise PaymentRequiredError(
            message="Payment rejected after signing",
            payment_requirements=requirements,
            headers=dict(retry_response.headers),
        )

    return retry_response
