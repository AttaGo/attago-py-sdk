"""Shared pytest fixtures for the AttaGo Python SDK test suite."""

from __future__ import annotations

import pytest
import httpx


@pytest.fixture
def mock_transport():
    """Factory for creating httpx.MockTransport from a handler function.

    Usage::

        def test_something(mock_transport):
            def handler(request):
                return httpx.Response(200, json={"ok": True})
            transport = mock_transport(handler)
    """
    def _make(handler):
        return httpx.MockTransport(handler)
    return _make
