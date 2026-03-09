"""Tests for attago.auth -- Cognito REST authentication."""

from __future__ import annotations

import httpx
import pytest
import respx

from attago.auth import (
    CognitoAuth,
    confirm_forgot_password,
    confirm_sign_up,
    forgot_password,
    sign_up,
)
from attago.errors import AuthError, MfaRequiredError
from attago.types import CognitoTokens

COGNITO_URL = "https://cognito-idp.us-east-1.amazonaws.com/"


# ── CognitoAuth.sign_in ─────────────────────────────────────────────


@pytest.mark.asyncio
async def test_sign_in_success() -> None:
    """Successful sign-in stores tokens and returns CognitoTokens."""
    with respx.mock:
        respx.post(COGNITO_URL).mock(
            return_value=httpx.Response(
                200,
                json={
                    "AuthenticationResult": {
                        "IdToken": "id-token-abc",
                        "AccessToken": "access-token-xyz",
                        "RefreshToken": "refresh-token-123",
                    }
                },
            )
        )

        auth = CognitoAuth("test-client-id")
        tokens = await auth.sign_in("user@example.com", "password123")

        assert tokens.id_token == "id-token-abc"
        assert tokens.access_token == "access-token-xyz"
        assert tokens.refresh_token == "refresh-token-123"
        # Tokens are also cached internally
        assert auth.get_tokens() is tokens


@pytest.mark.asyncio
async def test_sign_in_mfa_challenge() -> None:
    """MFA challenge raises MfaRequiredError with session and challenge name."""
    with respx.mock:
        respx.post(COGNITO_URL).mock(
            return_value=httpx.Response(
                200,
                json={
                    "ChallengeName": "SOFTWARE_TOKEN_MFA",
                    "Session": "session-token-xyz",
                },
            )
        )

        auth = CognitoAuth("test-client-id")
        with pytest.raises(MfaRequiredError) as exc_info:
            await auth.sign_in("user@example.com", "password123")

        err = exc_info.value
        assert err.session == "session-token-xyz"
        assert err.challenge_name == "SOFTWARE_TOKEN_MFA"
        # Tokens should NOT be set on MFA challenge
        assert auth.get_tokens() is None


@pytest.mark.asyncio
async def test_sign_in_auth_error() -> None:
    """Cognito 400 raises AuthError with code and message."""
    with respx.mock:
        respx.post(COGNITO_URL).mock(
            return_value=httpx.Response(
                400,
                json={
                    "__type": "NotAuthorizedException",
                    "message": "Incorrect username or password",
                },
            )
        )

        auth = CognitoAuth("test-client-id")
        with pytest.raises(AuthError) as exc_info:
            await auth.sign_in("user@example.com", "wrong-password")

        err = exc_info.value
        assert err.code == "NotAuthorizedException"
        assert "Incorrect username or password" in err.message


# ── Token management ─────────────────────────────────────────────────


def test_set_tokens_get_id_token() -> None:
    """set_tokens + get_tokens round-trip works."""
    auth = CognitoAuth("test-client-id")
    tokens = CognitoTokens(
        id_token="preset-id-token",
        access_token="preset-access",
        refresh_token="preset-refresh",
    )
    auth.set_tokens(tokens)
    assert auth.get_tokens() is tokens
    assert auth.get_tokens().id_token == "preset-id-token"


@pytest.mark.asyncio
async def test_get_id_token_returns_cached() -> None:
    """get_id_token returns the cached ID token without network call."""
    auth = CognitoAuth("test-client-id")
    auth.set_tokens(
        CognitoTokens(
            id_token="cached-id",
            access_token="cached-access",
            refresh_token="cached-refresh",
        )
    )
    token = await auth.get_id_token()
    assert token == "cached-id"


@pytest.mark.asyncio
async def test_get_id_token_no_tokens_auto_signin() -> None:
    """get_id_token auto-signs in when email/password are set."""
    with respx.mock:
        respx.post(COGNITO_URL).mock(
            return_value=httpx.Response(
                200,
                json={
                    "AuthenticationResult": {
                        "IdToken": "auto-id-token",
                        "AccessToken": "auto-access",
                        "RefreshToken": "auto-refresh",
                    }
                },
            )
        )

        auth = CognitoAuth(
            "test-client-id",
            email="user@example.com",
            password="password123",
        )
        token = await auth.get_id_token()
        assert token == "auto-id-token"


@pytest.mark.asyncio
async def test_get_id_token_no_tokens_no_creds_raises() -> None:
    """get_id_token raises AuthError when no tokens and no credentials."""
    auth = CognitoAuth("test-client-id")
    with pytest.raises(AuthError, match="No tokens available"):
        await auth.get_id_token()


def test_sign_out_clears_tokens() -> None:
    """sign_out clears cached tokens."""
    auth = CognitoAuth("test-client-id")
    auth.set_tokens(CognitoTokens("x", "y", "z"))
    auth.sign_out()
    assert auth.get_tokens() is None


# ── RespondToMFA ─────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_respond_to_mfa_success() -> None:
    """Successful MFA response stores tokens."""
    with respx.mock:
        respx.post(COGNITO_URL).mock(
            return_value=httpx.Response(
                200,
                json={
                    "AuthenticationResult": {
                        "IdToken": "mfa-id-token",
                        "AccessToken": "mfa-access-token",
                        "RefreshToken": "mfa-refresh-token",
                    }
                },
            )
        )

        auth = CognitoAuth("test-client-id")
        tokens = await auth.respond_to_mfa("session-123", "654321")

        assert tokens.id_token == "mfa-id-token"
        assert auth.get_tokens() is tokens


# ── Module-level helpers ─────────────────────────────────────────────


@pytest.mark.asyncio
async def test_sign_up_success() -> None:
    """sign_up returns UserSub on success."""
    with respx.mock:
        respx.post(COGNITO_URL).mock(
            return_value=httpx.Response(
                200,
                json={
                    "UserConfirmed": False,
                    "UserSub": "abc-123-def-456",
                },
            )
        )

        user_sub = await sign_up(
            email="new@example.com",
            password="SecurePass1!",
            client_id="test-client-id",
        )
        assert user_sub == "abc-123-def-456"


@pytest.mark.asyncio
async def test_confirm_sign_up_success() -> None:
    """confirm_sign_up completes without error on 200."""
    with respx.mock:
        respx.post(COGNITO_URL).mock(
            return_value=httpx.Response(200, json={})
        )

        # Should not raise
        await confirm_sign_up(
            email="new@example.com",
            code="123456",
            client_id="test-client-id",
        )


@pytest.mark.asyncio
async def test_forgot_password_success() -> None:
    """forgot_password completes without error on 200."""
    with respx.mock:
        respx.post(COGNITO_URL).mock(
            return_value=httpx.Response(
                200,
                json={"CodeDeliveryDetails": {"Destination": "n***@e***.com"}},
            )
        )

        await forgot_password(
            email="user@example.com",
            client_id="test-client-id",
        )


@pytest.mark.asyncio
async def test_confirm_forgot_password_success() -> None:
    """confirm_forgot_password completes without error on 200."""
    with respx.mock:
        respx.post(COGNITO_URL).mock(
            return_value=httpx.Response(200, json={})
        )

        await confirm_forgot_password(
            email="user@example.com",
            code="123456",
            new_password="NewSecurePass1!",
            client_id="test-client-id",
        )


# ── Request shape verification ───────────────────────────────────────


@pytest.mark.asyncio
async def test_sign_in_sends_correct_headers_and_body() -> None:
    """Verify the Cognito request has correct headers and body shape."""
    with respx.mock:
        route = respx.post(COGNITO_URL).mock(
            return_value=httpx.Response(
                200,
                json={
                    "AuthenticationResult": {
                        "IdToken": "tok",
                        "AccessToken": "acc",
                        "RefreshToken": "ref",
                    }
                },
            )
        )

        auth = CognitoAuth("my-client-id", region="eu-west-1")
        # Override the URL by using the default region mock
        # (respx catches all posts to the cognito URL regardless of region)
        auth._region = "us-east-1"
        await auth.sign_in("alice@example.com", "s3cret")

        req = route.calls.last.request
        assert req.headers["content-type"] == "application/x-amz-json-1.1"
        assert (
            req.headers["x-amz-target"]
            == "AWSCognitoIdentityProviderService.InitiateAuth"
        )

        import json

        body = json.loads(req.content)
        assert body["AuthFlow"] == "USER_PASSWORD_AUTH"
        assert body["ClientId"] == "my-client-id"
        assert body["AuthParameters"]["USERNAME"] == "alice@example.com"
        assert body["AuthParameters"]["PASSWORD"] == "s3cret"
