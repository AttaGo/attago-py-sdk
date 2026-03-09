"""Webhook listener -- threaded HTTP server with HMAC verification."""

from __future__ import annotations

import hashlib
import hmac
import json
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Any, Callable

from .types import WebhookPayload


def _verify_signature(body: bytes, secret: str, signature: str) -> bool:
    """HMAC-SHA256 signature verification (constant-time)."""
    expected = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)


class WebhookListener:
    """Threaded HTTP server for receiving AttaGo webhook deliveries.

    HMAC-SHA256 signature verification is enforced on every request.

    Usage::

        listener = WebhookListener(secret="whsec_...", port=4000)
        listener.on_alert(lambda payload: print(payload.alert.token))
        listener.on_test(lambda payload: print("test received"))
        listener.start()
        # ...
        listener.stop()

    Parameters
    ----------
    secret:
        Webhook secret for HMAC verification.
    port:
        Port to listen on (0 for OS-assigned).
    host:
        Host to bind to.
    path:
        URL path to accept webhooks on.
    """

    def __init__(
        self,
        *,
        secret: str,
        port: int = 4000,
        host: str = "127.0.0.1",
        path: str = "/webhook",
    ) -> None:
        self._secret = secret
        self._port = port
        self._host = host
        self._path = path
        self._alert_handlers: list[Callable[[WebhookPayload], None]] = []
        self._test_handlers: list[Callable[[WebhookPayload], None]] = []
        self._error_handlers: list[Callable[[Exception], None]] = []
        self._server: HTTPServer | None = None
        self._thread: threading.Thread | None = None

    def on_alert(self, handler: Callable[[WebhookPayload], None]) -> None:
        """Register a handler for alert events."""
        self._alert_handlers.append(handler)

    def on_test(self, handler: Callable[[WebhookPayload], None]) -> None:
        """Register a handler for test events."""
        self._test_handlers.append(handler)

    def on_error(self, handler: Callable[[Exception], None]) -> None:
        """Register an error handler."""
        self._error_handlers.append(handler)

    def start(self) -> None:
        """Start the listener in a background thread.

        Raises RuntimeError if already started.
        """
        if self._server is not None:
            raise RuntimeError("Listener is already running")

        listener = self  # capture for handler class

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):  # noqa: N802
                # Wrong path -> 404
                if self.path != listener._path:
                    self.send_response(404)
                    self.end_headers()
                    return

                # Read body
                content_length = int(self.headers.get("Content-Length", 0))
                body = self.rfile.read(content_length)

                # Verify signature
                signature = self.headers.get("X-AttaGo-Signature", "")
                if not signature or not _verify_signature(
                    body, listener._secret, signature
                ):
                    self.send_response(401)
                    self.end_headers()
                    return

                # Parse and dispatch
                try:
                    data = json.loads(body)
                    payload = WebhookPayload.from_dict(data)

                    if payload.event == "alert":
                        for h in listener._alert_handlers:
                            try:
                                h(payload)
                            except Exception as exc:
                                listener._emit_error(exc)
                    elif payload.event == "test":
                        for h in listener._test_handlers:
                            try:
                                h(payload)
                            except Exception as exc:
                                listener._emit_error(exc)

                    self.send_response(200)
                    self.end_headers()
                except Exception as exc:
                    listener._emit_error(exc)
                    self.send_response(500)
                    self.end_headers()

            def log_message(self, format, *args):  # noqa: A002
                pass  # Suppress default logging

        self._server = HTTPServer((self._host, self._port), Handler)
        self._thread = threading.Thread(
            target=self._server.serve_forever, daemon=True
        )
        self._thread.start()

    def stop(self) -> None:
        """Shut down the listener."""
        if self._server is not None:
            self._server.shutdown()
            self._server = None
        if self._thread is not None:
            self._thread.join(timeout=5)
            self._thread = None

    @property
    def addr(self) -> str:
        """Return the bound address as ``host:port``."""
        if self._server is not None:
            host, port = self._server.server_address
            return f"{host}:{port}"
        return ""

    @property
    def listening(self) -> bool:
        """Whether the server is running."""
        return self._server is not None

    def _emit_error(self, exc: Exception) -> None:
        """Send an exception to registered error handlers."""
        for h in self._error_handlers:
            try:
                h(exc)
            except Exception:
                pass  # Don't let error handler errors crash

    # -- Context manager support ------------------------------------------

    def __enter__(self) -> WebhookListener:
        self.start()
        return self

    def __exit__(self, *exc: Any) -> None:
        self.stop()
