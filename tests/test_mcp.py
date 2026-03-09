"""Tests for attago.mcp -- McpService."""

from __future__ import annotations

import json

import httpx
import pytest

from attago.client import AttaGoClient
from attago.errors import McpError
from attago.mcp import McpService


# ── Helpers ──────────────────────────────────────────────────────────

INIT_RESULT = {
    "protocolVersion": "2025-03-26",
    "capabilities": {"tools": {"listChanged": False}},
    "serverInfo": {"name": "attago-mcp", "version": "1.0.0"},
    "instructions": "Use tools to access data",
}

TOOLS_RESULT = {
    "tools": [
        {
            "name": "get_score",
            "description": "Get Go/No-Go score",
            "inputSchema": {
                "type": "object",
                "properties": {"symbol": {"type": "string"}},
            },
            "annotations": {"x402Price": "0.10"},
        },
        {
            "name": "get_data",
            "description": "Get full market data",
            "inputSchema": {
                "type": "object",
                "properties": {"symbols": {"type": "string"}},
            },
        },
    ],
}

CALL_RESULT = {
    "content": [
        {"type": "text", "text": '{"score": 72.5, "signal": "GO"}'},
    ],
    "isError": False,
}


def _ok_response(body_id: int, result: dict) -> dict:
    """Build a successful JSON-RPC 2.0 response."""
    return {"jsonrpc": "2.0", "id": body_id, "result": result}


def _error_response(body_id: int, code: int, message: str, data: str | None = None) -> dict:
    """Build a JSON-RPC 2.0 error response."""
    err: dict = {"code": code, "message": message}
    if data is not None:
        err["data"] = data
    return {"jsonrpc": "2.0", "id": body_id, "error": err}


# ── Async tests ──────────────────────────────────────────────────────


class TestMcpServiceAsync:
    @pytest.mark.asyncio
    async def test_initialize(self) -> None:
        """initialize sends correct JSON-RPC envelope and returns McpServerInfo."""

        def handler(request: httpx.Request) -> httpx.Response:
            body = json.loads(request.content)
            assert body["jsonrpc"] == "2.0"
            assert body["method"] == "initialize"
            assert body["params"]["protocolVersion"] == "2025-03-26"
            assert body["params"]["clientInfo"]["name"] == "attago-python"
            return httpx.Response(200, json=_ok_response(body["id"], INIT_RESULT))

        async with AttaGoClient(
            api_key="test",
            base_url="https://api.test.com",
            transport=httpx.MockTransport(handler),
        ) as client:
            svc = McpService(client)
            info = await svc.initialize()

        assert info.protocol_version == "2025-03-26"
        assert info.server_info.name == "attago-mcp"
        assert info.server_info.version == "1.0.0"
        assert info.capabilities.tools is not None
        assert info.capabilities.tools.list_changed is False
        assert info.instructions == "Use tools to access data"

    @pytest.mark.asyncio
    async def test_list_tools(self) -> None:
        """list_tools returns a list of McpTool objects."""

        def handler(request: httpx.Request) -> httpx.Response:
            body = json.loads(request.content)
            assert body["method"] == "tools/list"
            assert "params" not in body
            return httpx.Response(200, json=_ok_response(body["id"], TOOLS_RESULT))

        async with AttaGoClient(
            api_key="test",
            base_url="https://api.test.com",
            transport=httpx.MockTransport(handler),
        ) as client:
            svc = McpService(client)
            tools = await svc.list_tools()

        assert len(tools) == 2
        assert tools[0].name == "get_score"
        assert tools[0].description == "Get Go/No-Go score"
        assert tools[0].input_schema["type"] == "object"
        assert tools[0].annotations == {"x402Price": "0.10"}
        assert tools[1].name == "get_data"
        assert tools[1].annotations is None

    @pytest.mark.asyncio
    async def test_call_tool(self) -> None:
        """call_tool sends tools/call with name and arguments."""

        def handler(request: httpx.Request) -> httpx.Response:
            body = json.loads(request.content)
            assert body["method"] == "tools/call"
            assert body["params"]["name"] == "get_score"
            assert body["params"]["arguments"] == {"symbol": "BTC"}
            return httpx.Response(200, json=_ok_response(body["id"], CALL_RESULT))

        async with AttaGoClient(
            api_key="test",
            base_url="https://api.test.com",
            transport=httpx.MockTransport(handler),
        ) as client:
            svc = McpService(client)
            result = await svc.call_tool("get_score", {"symbol": "BTC"})

        assert result.is_error is False
        assert len(result.content) == 1
        assert result.content[0].type == "text"
        assert '"score": 72.5' in result.content[0].text

    @pytest.mark.asyncio
    async def test_ping(self) -> None:
        """ping sends ping method and returns None on empty result."""

        def handler(request: httpx.Request) -> httpx.Response:
            body = json.loads(request.content)
            assert body["method"] == "ping"
            assert "params" not in body
            return httpx.Response(200, json=_ok_response(body["id"], {}))

        async with AttaGoClient(
            api_key="test",
            base_url="https://api.test.com",
            transport=httpx.MockTransport(handler),
        ) as client:
            svc = McpService(client)
            # ping returns None -- should not raise
            await svc.ping()

    @pytest.mark.asyncio
    async def test_json_rpc_error_raises_mcp_error(self) -> None:
        """A JSON-RPC error response raises McpError with correct fields."""

        def handler(request: httpx.Request) -> httpx.Response:
            body = json.loads(request.content)
            return httpx.Response(
                200, json=_error_response(body["id"], -32601, "Method not found"),
            )

        async with AttaGoClient(
            api_key="test",
            base_url="https://api.test.com",
            transport=httpx.MockTransport(handler),
        ) as client:
            svc = McpService(client)
            with pytest.raises(McpError) as exc_info:
                await svc.initialize()
            assert exc_info.value.code == -32601
            assert exc_info.value.message == "Method not found"
            assert exc_info.value.data is None

    @pytest.mark.asyncio
    async def test_json_rpc_error_with_data(self) -> None:
        """McpError includes the optional data field when present."""

        def handler(request: httpx.Request) -> httpx.Response:
            body = json.loads(request.content)
            return httpx.Response(
                200, json=_error_response(body["id"], -32600, "Invalid", "extra info"),
            )

        async with AttaGoClient(
            api_key="test",
            base_url="https://api.test.com",
            transport=httpx.MockTransport(handler),
        ) as client:
            svc = McpService(client)
            with pytest.raises(McpError) as exc_info:
                await svc.ping()
            assert exc_info.value.code == -32600
            assert exc_info.value.data == "extra info"

    @pytest.mark.asyncio
    async def test_auto_increment_ids(self) -> None:
        """Each RPC call gets an incrementing integer ID."""
        ids_seen: list[int] = []

        def handler(request: httpx.Request) -> httpx.Response:
            body = json.loads(request.content)
            ids_seen.append(body["id"])
            return httpx.Response(200, json=_ok_response(body["id"], {}))

        async with AttaGoClient(
            api_key="test",
            base_url="https://api.test.com",
            transport=httpx.MockTransport(handler),
        ) as client:
            svc = McpService(client)
            await svc.ping()
            await svc.ping()
            await svc.ping()

        assert ids_seen == [1, 2, 3]

    @pytest.mark.asyncio
    async def test_api_key_header_sent(self) -> None:
        """The X-API-Key header is included in MCP requests."""

        def handler(request: httpx.Request) -> httpx.Response:
            assert request.headers["X-API-Key"] == "ak_test_123"
            assert request.headers["Content-Type"] == "application/json"
            body = json.loads(request.content)
            return httpx.Response(200, json=_ok_response(body["id"], {}))

        async with AttaGoClient(
            api_key="ak_test_123",
            base_url="https://api.test.com",
            transport=httpx.MockTransport(handler),
        ) as client:
            svc = McpService(client)
            await svc.ping()

    @pytest.mark.asyncio
    async def test_call_tool_with_is_error(self) -> None:
        """call_tool correctly surfaces isError: true from the server."""
        error_result = {
            "content": [{"type": "text", "text": "Token not found"}],
            "isError": True,
        }

        def handler(request: httpx.Request) -> httpx.Response:
            body = json.loads(request.content)
            return httpx.Response(200, json=_ok_response(body["id"], error_result))

        async with AttaGoClient(
            api_key="test",
            base_url="https://api.test.com",
            transport=httpx.MockTransport(handler),
        ) as client:
            svc = McpService(client)
            result = await svc.call_tool("get_score", {"symbol": "FAKE"})

        assert result.is_error is True
        assert result.content[0].text == "Token not found"

    @pytest.mark.asyncio
    async def test_call_tool_no_arguments(self) -> None:
        """call_tool with no arguments sends an empty dict."""

        def handler(request: httpx.Request) -> httpx.Response:
            body = json.loads(request.content)
            assert body["params"]["arguments"] == {}
            return httpx.Response(200, json=_ok_response(body["id"], CALL_RESULT))

        async with AttaGoClient(
            api_key="test",
            base_url="https://api.test.com",
            transport=httpx.MockTransport(handler),
        ) as client:
            svc = McpService(client)
            await svc.call_tool("get_data")

    @pytest.mark.asyncio
    async def test_url_targets_v1_mcp(self) -> None:
        """All MCP requests POST to /v1/mcp."""
        captured_url: str | None = None

        def handler(request: httpx.Request) -> httpx.Response:
            nonlocal captured_url
            captured_url = str(request.url)
            body = json.loads(request.content)
            return httpx.Response(200, json=_ok_response(body["id"], {}))

        async with AttaGoClient(
            api_key="test",
            base_url="https://api.test.com",
            transport=httpx.MockTransport(handler),
        ) as client:
            svc = McpService(client)
            await svc.ping()

        assert captured_url == "https://api.test.com/v1/mcp"


# ── Sync tests ───────────────────────────────────────────────────────


class TestMcpServiceSync:
    def test_initialize_sync(self) -> None:
        """initialize_sync returns McpServerInfo via sync client."""

        def handler(request: httpx.Request) -> httpx.Response:
            body = json.loads(request.content)
            return httpx.Response(200, json=_ok_response(body["id"], INIT_RESULT))

        client = AttaGoClient(
            api_key="test",
            base_url="https://api.test.com",
            sync=True,
            sync_transport=httpx.MockTransport(handler),
        )
        with client:
            svc = McpService(client)
            info = svc.initialize_sync()

        assert info.protocol_version == "2025-03-26"
        assert info.server_info.name == "attago-mcp"

    def test_ping_sync(self) -> None:
        """ping_sync completes without error."""

        def handler(request: httpx.Request) -> httpx.Response:
            body = json.loads(request.content)
            return httpx.Response(200, json=_ok_response(body["id"], {}))

        client = AttaGoClient(
            api_key="test",
            base_url="https://api.test.com",
            sync=True,
            sync_transport=httpx.MockTransport(handler),
        )
        with client:
            svc = McpService(client)
            svc.ping_sync()

    def test_call_tool_sync(self) -> None:
        """call_tool_sync returns McpToolCallResult."""

        def handler(request: httpx.Request) -> httpx.Response:
            body = json.loads(request.content)
            return httpx.Response(200, json=_ok_response(body["id"], CALL_RESULT))

        client = AttaGoClient(
            api_key="test",
            base_url="https://api.test.com",
            sync=True,
            sync_transport=httpx.MockTransport(handler),
        )
        with client:
            svc = McpService(client)
            result = svc.call_tool_sync("get_score", {"symbol": "BTC"})

        assert result.is_error is False
        assert len(result.content) == 1
