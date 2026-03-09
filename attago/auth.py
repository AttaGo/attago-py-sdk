"""Cognito JWT authentication (REST, no AWS SDK).

Mirrors the Go SDK's ``auth.go`` -- direct HTTP calls to the Cognito
Identity Provider endpoint.  No ``boto3`` or ``aws-sdk`` dependency.
"""

from __future__ import annotations

from typing import Any

import httpx

from .errors import AuthError, MfaRequiredError
from .types import CognitoTokens, DEFAULT_COGNITO_REGION


# ── Internal helper ──────────────────────────────────────────────────


async def _cognito_request(
    region: str,
    target: str,
    body: dict[str, Any],
    http_client: httpx.AsyncClient | None = None,
) -> dict[str, Any]:
    """POST to Cognito IDP endpoint.

    Parameters
    ----------
    region:
        AWS region (e.g. ``us-east-1``).
    target:
        The ``X-Amz-Target`` action, e.g.
        ``AWSCognitoIdentityProviderService.InitiateAuth``.
    body:
        JSON-serialisable request body.
    http_client:
        Optional pre-configured ``httpx.AsyncClient``.  A throwaway client
        is created when *None* (fine for standalone helpers; the class
        methods always pass their own client).
    """
    url = f"https://cognito-idp.{region}.amazonaws.com/"
    headers = {
        "Content-Type": "application/x-amz-json-1.1",
        "X-Amz-Target": target,
    }
    owns_client = http_client is None
    client = http_client or httpx.AsyncClient()
    try:
        resp = await client.post(url, json=body, headers=headers)
    finally:
        if owns_client:
            await client.aclose()

    data: dict[str, Any] = resp.json()

    if resp.status_code >= 400:
        msg = data.get("message", f"Cognito error {resp.status_code}")
        code = data.get("__type")
        raise AuthError(msg, code)

    return data


def _extract_tokens(result: dict[str, Any]) -> CognitoTokens:
    """Pull ``CognitoTokens`` out of an ``AuthenticationResult`` map."""
    auth_result = result.get("AuthenticationResult")
    if not isinstance(auth_result, dict):
        raise AuthError("Missing AuthenticationResult in Cognito response")
    id_token = auth_result.get("IdToken", "")
    if not id_token:
        raise AuthError("Missing IdToken in Cognito response")
    return CognitoTokens(
        id_token=id_token,
        access_token=auth_result.get("AccessToken", ""),
        refresh_token=auth_result.get("RefreshToken", ""),
    )


# ── CognitoAuth class ───────────────────────────────────────────────


class CognitoAuth:
    """Manages Cognito authentication tokens.

    Typically accessed via ``client.auth`` rather than instantiated
    directly.
    """

    def __init__(
        self,
        client_id: str,
        region: str = DEFAULT_COGNITO_REGION,
        http_client: httpx.AsyncClient | None = None,
        email: str | None = None,
        password: str | None = None,
    ) -> None:
        self._client_id = client_id
        self._region = region
        self._http = http_client or httpx.AsyncClient()
        self._email = email or ""
        self._password = password or ""
        self._tokens: CognitoTokens | None = None

    # ── sign-in / sign-out ───────────────────────────────────────────

    async def sign_in(
        self,
        email: str | None = None,
        password: str | None = None,
    ) -> CognitoTokens:
        """Sign in with email/password.

        Parameters are optional -- if omitted the values supplied at
        construction time are used.

        Raises
        ------
        MfaRequiredError
            If the account has MFA enabled.  Catch the error and call
            :meth:`respond_to_mfa` with the ``session`` and TOTP code.
        AuthError
            On any other Cognito error (bad password, user not found, etc.).
        """
        email = email or self._email
        password = password or self._password

        body: dict[str, Any] = {
            "AuthFlow": "USER_PASSWORD_AUTH",
            "ClientId": self._client_id,
            "AuthParameters": {
                "USERNAME": email,
                "PASSWORD": password,
            },
        }

        result = await _cognito_request(
            self._region,
            "AWSCognitoIdentityProviderService.InitiateAuth",
            body,
            self._http,
        )

        # MFA challenge?
        challenge = result.get("ChallengeName")
        if isinstance(challenge, str):
            session = result.get("Session", "")
            raise MfaRequiredError(session=session, challenge_name=challenge)

        tokens = _extract_tokens(result)
        self._tokens = tokens
        return tokens

    def sign_out(self) -> None:
        """Clear cached tokens."""
        self._tokens = None

    # ── token access ─────────────────────────────────────────────────

    async def get_id_token(self) -> str:
        """Return a valid ID token, auto-signing in if possible.

        Raises
        ------
        AuthError
            If no tokens are cached and no email/password were provided.
        """
        if self._tokens is not None and self._tokens.id_token:
            return self._tokens.id_token

        if self._email and self._password:
            await self.sign_in()
            assert self._tokens is not None  # sign_in sets _tokens
            return self._tokens.id_token

        raise AuthError("No tokens available. Call sign_in() first.")

    def get_tokens(self) -> CognitoTokens | None:
        """Return the current token set (for persistence)."""
        return self._tokens

    def set_tokens(self, tokens: CognitoTokens) -> None:
        """Restore a previously persisted token set."""
        self._tokens = tokens

    # ── MFA ──────────────────────────────────────────────────────────

    async def respond_to_mfa(
        self,
        session: str,
        code: str,
    ) -> CognitoTokens:
        """Complete an MFA challenge.

        Parameters
        ----------
        session:
            The session string from :class:`MfaRequiredError`.
        code:
            The 6-digit TOTP code from the authenticator app.
        """
        body: dict[str, Any] = {
            "ChallengeName": "SOFTWARE_TOKEN_MFA",
            "ClientId": self._client_id,
            "Session": session,
            "ChallengeResponses": {
                "SOFTWARE_TOKEN_MFA_CODE": code,
            },
        }

        result = await _cognito_request(
            self._region,
            "AWSCognitoIdentityProviderService.RespondToAuthChallenge",
            body,
            self._http,
        )

        tokens = _extract_tokens(result)
        self._tokens = tokens
        return tokens


# ── Module-level registration helpers (no auth state needed) ─────────


async def sign_up(
    email: str,
    password: str,
    client_id: str,
    region: str = DEFAULT_COGNITO_REGION,
    http_client: httpx.AsyncClient | None = None,
) -> str:
    """Create a new account.  Sends a verification code to *email*.

    Returns the ``UserSub`` (Cognito user ID).
    """
    body: dict[str, Any] = {
        "ClientId": client_id,
        "Username": email,
        "Password": password,
        "UserAttributes": [
            {"Name": "email", "Value": email},
        ],
    }
    result = await _cognito_request(
        region,
        "AWSCognitoIdentityProviderService.SignUp",
        body,
        http_client,
    )
    return result.get("UserSub", "")


async def confirm_sign_up(
    email: str,
    code: str,
    client_id: str,
    region: str = DEFAULT_COGNITO_REGION,
    http_client: httpx.AsyncClient | None = None,
) -> None:
    """Confirm a new account with the emailed verification code."""
    body: dict[str, Any] = {
        "ClientId": client_id,
        "Username": email,
        "ConfirmationCode": code,
    }
    await _cognito_request(
        region,
        "AWSCognitoIdentityProviderService.ConfirmSignUp",
        body,
        http_client,
    )


async def forgot_password(
    email: str,
    client_id: str,
    region: str = DEFAULT_COGNITO_REGION,
    http_client: httpx.AsyncClient | None = None,
) -> None:
    """Trigger a password-reset email."""
    body: dict[str, Any] = {
        "ClientId": client_id,
        "Username": email,
    }
    await _cognito_request(
        region,
        "AWSCognitoIdentityProviderService.ForgotPassword",
        body,
        http_client,
    )


async def confirm_forgot_password(
    email: str,
    code: str,
    new_password: str,
    client_id: str,
    region: str = DEFAULT_COGNITO_REGION,
    http_client: httpx.AsyncClient | None = None,
) -> None:
    """Complete a password reset with the emailed code."""
    body: dict[str, Any] = {
        "ClientId": client_id,
        "Username": email,
        "ConfirmationCode": code,
        "Password": new_password,
    }
    await _cognito_request(
        region,
        "AWSCognitoIdentityProviderService.ConfirmForgotPassword",
        body,
        http_client,
    )
