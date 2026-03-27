"""Tests for attago.messaging -- MessagingService CRUD + test delivery."""

from __future__ import annotations

import json

import httpx
import pytest

from attago.client import AttaGoClient
from attago.messaging import MessagingService


# -- Helpers ----------------------------------------------------------------


def _make_client(handler) -> AttaGoClient:
    """Create an async AttaGoClient with a mock transport."""
    return AttaGoClient(
        api_key="ak_test",
        base_url="https://api.test.com",
        transport=httpx.MockTransport(handler),
    )


# -- MessagingService -------------------------------------------------------


class TestMessagingService:
    @pytest.mark.asyncio
    async def test_list(self) -> None:
        """GET /user/messaging returns list[MessagingLink]."""

        def handler(request: httpx.Request) -> httpx.Response:
            assert request.method == "GET"
            assert "/v1/user/messaging" in str(request.url)
            return httpx.Response(200, json={
                "channels": [
                    {
                        "platform": "telegram",
                        "username": "alice_bot",
                        "linkedAt": "2026-03-01T00:00:00Z",
                    },
                ]
            })

        async with _make_client(handler) as client:
            svc = MessagingService(client)
            result = await svc.list()

        assert len(result) == 1
        assert result[0].platform == "telegram"
        assert result[0].username == "alice_bot"
        assert result[0].linked_at == "2026-03-01T00:00:00Z"

    @pytest.mark.asyncio
    async def test_list_empty(self) -> None:
        """GET /user/messaging with no channels returns empty list."""

        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json={"channels": []})

        async with _make_client(handler) as client:
            svc = MessagingService(client)
            result = await svc.list()

        assert result == []

    @pytest.mark.asyncio
    async def test_link_telegram(self) -> None:
        """POST /user/messaging/telegram/link sends code and returns result."""
        captured_body = None

        def handler(request: httpx.Request) -> httpx.Response:
            nonlocal captured_body
            assert request.method == "POST"
            assert "/v1/user/messaging/telegram/link" in str(request.url)
            captured_body = json.loads(request.content)
            return httpx.Response(200, json={
                "linked": True,
                "username": "alice_bot",
            })

        async with _make_client(handler) as client:
            svc = MessagingService(client)
            result = await svc.link_telegram("ABC123")

        assert result.linked is True
        assert result.username == "alice_bot"
        assert captured_body == {"code": "ABC123"}

    @pytest.mark.asyncio
    async def test_unlink_telegram(self) -> None:
        """DELETE /user/messaging/telegram returns unlinked status."""

        def handler(request: httpx.Request) -> httpx.Response:
            assert request.method == "DELETE"
            assert "/v1/user/messaging/telegram" in str(request.url)
            return httpx.Response(200, json={"unlinked": True})

        async with _make_client(handler) as client:
            svc = MessagingService(client)
            result = await svc.unlink_telegram()

        assert result == {"unlinked": True}

    @pytest.mark.asyncio
    async def test_test(self) -> None:
        """POST /user/messaging/test returns MessagingTestResult."""

        def handler(request: httpx.Request) -> httpx.Response:
            assert request.method == "POST"
            assert "/v1/user/messaging/test" in str(request.url)
            return httpx.Response(200, json={
                "success": True,
                "platforms": ["telegram"],
            })

        async with _make_client(handler) as client:
            svc = MessagingService(client)
            result = await svc.test()

        assert result.success is True
        assert result.platforms == ["telegram"]
        assert result.error is None

    @pytest.mark.asyncio
    async def test_test_with_error(self) -> None:
        """POST /user/messaging/test with error field populated."""

        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json={
                "success": False,
                "platforms": [],
                "error": "No channels linked",
            })

        async with _make_client(handler) as client:
            svc = MessagingService(client)
            result = await svc.test()

        assert result.success is False
        assert result.platforms == []
        assert result.error == "No channels linked"


# -- Sync mode --------------------------------------------------------------


class TestMessagingServiceSync:
    def test_list_sync(self) -> None:
        """Sync mode: list() uses _request_sync."""

        def handler(request: httpx.Request) -> httpx.Response:
            assert request.method == "GET"
            assert "/v1/user/messaging" in str(request.url)
            return httpx.Response(200, json={
                "channels": [
                    {
                        "platform": "telegram",
                        "username": "bob_bot",
                        "linkedAt": "2026-03-02T00:00:00Z",
                    },
                ]
            })

        client = AttaGoClient(
            api_key="ak_test",
            base_url="https://api.test.com",
            sync=True,
            sync_transport=httpx.MockTransport(handler),
        )
        with client:
            svc = MessagingService(client)
            # In sync mode, the async method still works but uses sync path
            import asyncio
            result = asyncio.get_event_loop().run_until_complete(svc.list())

        assert len(result) == 1
        assert result[0].platform == "telegram"
        assert result[0].username == "bob_bot"
