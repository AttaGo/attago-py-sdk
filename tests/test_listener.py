"""Tests for the webhook listener (threaded HTTP server with HMAC verification)."""

from __future__ import annotations

import hashlib
import hmac
import json

import httpx
import pytest

from attago.listener import WebhookListener


def _sign(body: bytes, secret: str) -> str:
    return hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


def _make_payload(event: str = "alert", token: str = "BTC", state: str = "triggered"):
    return {
        "event": event,
        "version": "2",
        "environment": "production",
        "timestamp": "2026-01-01T00:00:00Z",
        "alert": {"id": "sub_123", "label": "Test", "token": token, "state": state},
        "data": {"url": None, "expiresAt": None, "fallbackUrl": None},
    }


SECRET = "whsec_test_secret"


class TestWebhookListener:
    def test_start_stop(self):
        listener = WebhookListener(secret=SECRET, port=0)
        listener.start()
        try:
            assert listener.listening
            assert listener.addr != ""
        finally:
            listener.stop()
        assert not listener.listening

    def test_double_start_raises(self):
        listener = WebhookListener(secret=SECRET, port=0)
        listener.start()
        try:
            with pytest.raises(RuntimeError):
                listener.start()
        finally:
            listener.stop()

    def test_valid_signature_200(self):
        received = []
        listener = WebhookListener(secret=SECRET, port=0)
        listener.on_alert(lambda p: received.append(p))
        listener.start()
        try:
            payload = _make_payload()
            body = json.dumps(payload).encode()
            sig = _sign(body, SECRET)
            resp = httpx.post(
                f"http://{listener.addr}/webhook",
                content=body,
                headers={
                    "X-AttaGo-Signature": sig,
                    "Content-Type": "application/json",
                },
            )
            assert resp.status_code == 200
            assert len(received) == 1
            assert received[0].alert.token == "BTC"
        finally:
            listener.stop()

    def test_invalid_signature_401(self):
        listener = WebhookListener(secret=SECRET, port=0)
        listener.start()
        try:
            payload = _make_payload()
            body = json.dumps(payload).encode()
            resp = httpx.post(
                f"http://{listener.addr}/webhook",
                content=body,
                headers={
                    "X-AttaGo-Signature": "wrong",
                    "Content-Type": "application/json",
                },
            )
            assert resp.status_code == 401
        finally:
            listener.stop()

    def test_missing_signature_401(self):
        listener = WebhookListener(secret=SECRET, port=0)
        listener.start()
        try:
            payload = _make_payload()
            body = json.dumps(payload).encode()
            resp = httpx.post(
                f"http://{listener.addr}/webhook",
                content=body,
                headers={"Content-Type": "application/json"},
            )
            assert resp.status_code == 401
        finally:
            listener.stop()

    def test_wrong_path_404(self):
        listener = WebhookListener(secret=SECRET, port=0)
        listener.start()
        try:
            resp = httpx.post(f"http://{listener.addr}/wrong-path")
            assert resp.status_code == 404
        finally:
            listener.stop()

    def test_test_event_routes_to_on_test(self):
        received = []
        listener = WebhookListener(secret=SECRET, port=0)
        listener.on_test(lambda p: received.append(p))
        listener.start()
        try:
            payload = _make_payload(event="test")
            body = json.dumps(payload).encode()
            sig = _sign(body, SECRET)
            resp = httpx.post(
                f"http://{listener.addr}/webhook",
                content=body,
                headers={
                    "X-AttaGo-Signature": sig,
                    "Content-Type": "application/json",
                },
            )
            assert resp.status_code == 200
            assert len(received) == 1
            assert received[0].event == "test"
        finally:
            listener.stop()

    def test_handler_exception_captured(self):
        errors = []
        listener = WebhookListener(secret=SECRET, port=0)
        listener.on_alert(lambda p: 1 / 0)  # Will raise ZeroDivisionError
        listener.on_error(lambda e: errors.append(e))
        listener.start()
        try:
            payload = _make_payload()
            body = json.dumps(payload).encode()
            sig = _sign(body, SECRET)
            resp = httpx.post(
                f"http://{listener.addr}/webhook",
                content=body,
                headers={
                    "X-AttaGo-Signature": sig,
                    "Content-Type": "application/json",
                },
            )
            assert resp.status_code == 200
            assert len(errors) == 1
            assert isinstance(errors[0], ZeroDivisionError)
        finally:
            listener.stop()

    def test_context_manager(self):
        with WebhookListener(secret=SECRET, port=0) as listener:
            assert listener.listening
        assert not listener.listening
