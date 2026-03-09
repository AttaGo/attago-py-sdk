"""Error classes for the AttaGo Python SDK.

Hierarchy:

    AttaGoError (base)
    +-- ApiError (HTTP 4xx/5xx)
    |   +-- PaymentRequiredError (402)
    |   +-- RateLimitError (429)
    +-- AuthError (Cognito)
    |   +-- MfaRequiredError
    +-- McpError (JSON-RPC 2.0)
"""

from __future__ import annotations

from typing import Any


class AttaGoError(Exception):
    """Base error for all AttaGo SDK errors."""


class ApiError(AttaGoError):
    """HTTP API error returned by the AttaGo API."""

    def __init__(
        self,
        status_code: int,
        message: str,
        body: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> None:
        self.status_code = status_code
        self.message = message
        self.body = body or {}
        self.headers = headers or {}
        super().__init__(str(self))

    def __str__(self) -> str:
        if self.message:
            return f"attago: HTTP {self.status_code}: {self.message}"
        return f"attago: HTTP {self.status_code}"


class PaymentRequiredError(ApiError):
    """402 Payment Required -- x402 payment needed.

    The ``payment_requirements`` field contains the decoded PAYMENT-REQUIRED
    header with accepted payment networks, amounts, and signing instructions.
    """

    def __init__(
        self,
        message: str,
        body: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        payment_requirements: Any | None = None,
    ) -> None:
        self.payment_requirements = payment_requirements
        super().__init__(402, message, body, headers)

    def __str__(self) -> str:
        return f"attago: payment required: {self.message}"


class RateLimitError(ApiError):
    """429 Too Many Requests -- rate limit or abuse ban."""

    def __init__(
        self,
        message: str,
        body: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        retry_after: int | None = None,
    ) -> None:
        self.retry_after = retry_after
        super().__init__(429, message, body, headers)

    def __str__(self) -> str:
        if self.retry_after is not None and self.retry_after > 0:
            return f"attago: rate limited (retry after {self.retry_after}s): {self.message}"
        return f"attago: rate limited: {self.message}"


class AuthError(AttaGoError):
    """Cognito authentication error."""

    def __init__(self, message: str, code: str | None = None) -> None:
        self.message = message
        self.code = code
        super().__init__(str(self))

    def __str__(self) -> str:
        if self.code:
            return f"attago: auth error [{self.code}]: {self.message}"
        return f"attago: auth error: {self.message}"


class MfaRequiredError(AuthError):
    """MFA is required to complete sign-in.

    Call ``client.auth.respond_to_mfa(error.session, totp_code)`` to finish
    authentication.
    """

    def __init__(self, session: str, challenge_name: str) -> None:
        self.session = session
        self.challenge_name = challenge_name
        super().__init__(
            message=f"MFA required ({challenge_name})",
            code=None,
        )

    def __str__(self) -> str:
        return f"attago: MFA required ({self.challenge_name})"


class McpError(AttaGoError):
    """JSON-RPC 2.0 error from the MCP server.

    This does NOT inherit from ApiError -- it is a separate branch.
    """

    def __init__(
        self,
        code: int,
        message: str,
        data: Any = None,
    ) -> None:
        self.code = code
        self.message = message
        self.data = data
        super().__init__(str(self))

    def __str__(self) -> str:
        return f"attago: MCP error {self.code}: {self.message}"
