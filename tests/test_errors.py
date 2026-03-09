"""Tests for attago.errors -- error hierarchy, formatting, and isinstance checks."""

from __future__ import annotations

import pytest

from attago.errors import (
    ApiError,
    AttaGoError,
    AuthError,
    McpError,
    MfaRequiredError,
    PaymentRequiredError,
    RateLimitError,
)


# ── Error message formatting ────────────────────────────────────────


class TestApiErrorMessage:
    def test_with_message(self) -> None:
        err = ApiError(404, "not found")
        assert str(err) == "attago: HTTP 404: not found"

    def test_without_message(self) -> None:
        err = ApiError(500, "")
        assert str(err) == "attago: HTTP 500"


class TestPaymentRequiredErrorMessage:
    def test_format(self) -> None:
        err = PaymentRequiredError("payment needed")
        assert str(err) == "attago: payment required: payment needed"

    def test_status_code_is_402(self) -> None:
        err = PaymentRequiredError("pay up")
        assert err.status_code == 402


class TestRateLimitErrorMessage:
    def test_with_retry_after(self) -> None:
        err = RateLimitError("slow down", retry_after=60)
        assert str(err) == "attago: rate limited (retry after 60s): slow down"

    def test_without_retry_after(self) -> None:
        err = RateLimitError("slow down")
        assert str(err) == "attago: rate limited: slow down"

    def test_retry_after_zero(self) -> None:
        err = RateLimitError("banned", retry_after=0)
        assert str(err) == "attago: rate limited: banned"

    def test_status_code_is_429(self) -> None:
        err = RateLimitError("too fast")
        assert err.status_code == 429


class TestAuthErrorMessage:
    def test_with_code(self) -> None:
        err = AuthError("bad password", code="NotAuthorizedException")
        assert str(err) == "attago: auth error [NotAuthorizedException]: bad password"

    def test_without_code(self) -> None:
        err = AuthError("session expired")
        assert str(err) == "attago: auth error: session expired"


class TestMfaRequiredErrorMessage:
    def test_format(self) -> None:
        err = MfaRequiredError(session="sess-abc", challenge_name="SOFTWARE_TOKEN_MFA")
        assert str(err) == "attago: MFA required (SOFTWARE_TOKEN_MFA)"


class TestMcpErrorMessage:
    def test_format(self) -> None:
        err = McpError(code=-32601, message="method not found")
        assert str(err) == "attago: MCP error -32601: method not found"


# ── isinstance hierarchy checks ────────────────────────────────────


class TestHierarchy:
    def test_api_error_is_attago_error(self) -> None:
        err = ApiError(500, "boom")
        assert isinstance(err, AttaGoError)

    def test_payment_required_is_api_error(self) -> None:
        err = PaymentRequiredError("pay")
        assert isinstance(err, ApiError)

    def test_payment_required_is_attago_error(self) -> None:
        err = PaymentRequiredError("pay")
        assert isinstance(err, AttaGoError)

    def test_rate_limit_is_api_error(self) -> None:
        err = RateLimitError("slow")
        assert isinstance(err, ApiError)

    def test_rate_limit_is_attago_error(self) -> None:
        err = RateLimitError("slow")
        assert isinstance(err, AttaGoError)

    def test_auth_error_is_attago_error(self) -> None:
        err = AuthError("fail")
        assert isinstance(err, AttaGoError)

    def test_mfa_required_is_auth_error(self) -> None:
        err = MfaRequiredError(session="s", challenge_name="SOFTWARE_TOKEN_MFA")
        assert isinstance(err, AuthError)

    def test_mfa_required_is_attago_error(self) -> None:
        err = MfaRequiredError(session="s", challenge_name="SOFTWARE_TOKEN_MFA")
        assert isinstance(err, AttaGoError)

    def test_mcp_error_is_attago_error(self) -> None:
        err = McpError(code=-32600, message="invalid request")
        assert isinstance(err, AttaGoError)


# ── Cross-hierarchy negative checks ────────────────────────────────


class TestNegativeHierarchy:
    def test_mcp_error_is_not_api_error(self) -> None:
        err = McpError(code=-32600, message="invalid")
        assert not isinstance(err, ApiError)

    def test_payment_required_is_not_auth_error(self) -> None:
        err = PaymentRequiredError("pay")
        assert not isinstance(err, AuthError)

    def test_auth_error_is_not_api_error(self) -> None:
        err = AuthError("fail")
        assert not isinstance(err, ApiError)

    def test_mfa_required_is_not_api_error(self) -> None:
        err = MfaRequiredError(session="s", challenge_name="MFA")
        assert not isinstance(err, ApiError)

    def test_api_error_is_not_auth_error(self) -> None:
        err = ApiError(400, "bad request")
        assert not isinstance(err, AuthError)


# ── Attribute access ────────────────────────────────────────────────


class TestAttributes:
    def test_api_error_attributes(self) -> None:
        body = {"error": "nope"}
        headers = {"x-request-id": "abc"}
        err = ApiError(403, "forbidden", body=body, headers=headers)
        assert err.status_code == 403
        assert err.message == "forbidden"
        assert err.body == body
        assert err.headers == headers

    def test_api_error_default_body_and_headers(self) -> None:
        err = ApiError(500, "oops")
        assert err.body == {}
        assert err.headers == {}

    def test_payment_required_payment_requirements(self) -> None:
        reqs = {"x402Version": 1, "accepts": []}
        err = PaymentRequiredError("pay", payment_requirements=reqs)
        assert err.payment_requirements == reqs

    def test_rate_limit_retry_after(self) -> None:
        err = RateLimitError("slow", retry_after=120)
        assert err.retry_after == 120

    def test_rate_limit_retry_after_none(self) -> None:
        err = RateLimitError("slow")
        assert err.retry_after is None

    def test_auth_error_code(self) -> None:
        err = AuthError("bad", code="UserNotFoundException")
        assert err.code == "UserNotFoundException"

    def test_mfa_required_session_and_challenge(self) -> None:
        err = MfaRequiredError(session="sess-xyz", challenge_name="SOFTWARE_TOKEN_MFA")
        assert err.session == "sess-xyz"
        assert err.challenge_name == "SOFTWARE_TOKEN_MFA"

    def test_mcp_error_attributes(self) -> None:
        err = McpError(code=-32700, message="parse error", data={"detail": "bad json"})
        assert err.code == -32700
        assert err.message == "parse error"
        assert err.data == {"detail": "bad json"}

    def test_mcp_error_data_default_none(self) -> None:
        err = McpError(code=-32600, message="invalid")
        assert err.data is None


# ── Catchability (raise / except) ───────────────────────────────────


class TestCatchability:
    def test_catch_payment_required_as_api_error(self) -> None:
        with pytest.raises(ApiError) as exc_info:
            raise PaymentRequiredError("pay")
        assert exc_info.value.status_code == 402

    def test_catch_mfa_required_as_auth_error(self) -> None:
        with pytest.raises(AuthError):
            raise MfaRequiredError(session="s", challenge_name="MFA")

    def test_catch_all_as_attago_error(self) -> None:
        errors = [
            ApiError(500, "server error"),
            PaymentRequiredError("pay"),
            RateLimitError("slow"),
            AuthError("fail"),
            MfaRequiredError(session="s", challenge_name="MFA"),
            McpError(code=-32600, message="invalid"),
        ]
        for err in errors:
            with pytest.raises(AttaGoError):
                raise err
