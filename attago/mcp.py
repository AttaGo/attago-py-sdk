"""MCP service -- JSON-RPC 2.0 client for the AttaGo MCP server."""

from __future__ import annotations

import json
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from .client import AttaGoClient

from .errors import McpError
from .types import McpServerInfo, McpTool, McpToolCallResult, VERSION


class McpService:
    """JSON-RPC 2.0 client for the AttaGo MCP server.

    Communicates via HTTP POST to ``/v1/mcp``.
    Auto-incrementing request IDs ensure unique correlation.

    Async usage::

        info = await client.mcp.initialize()
        tools = await client.mcp.list_tools()
        result = await client.mcp.call_tool("get_score", {"symbol": "BTC"})

    Sync usage::

        info = client.mcp.initialize_sync()
        tools = client.mcp.list_tools_sync()
        result = client.mcp.call_tool_sync("get_score", {"symbol": "BTC"})
    """

    def __init__(self, client: AttaGoClient) -> None:
        self._client = client
        self._next_id = 1

    # ── Internal helpers ─────────────────────────────────────────────

    def _next_request_id(self) -> int:
        """Return the next auto-incrementing request ID."""
        rid = self._next_id
        self._next_id += 1
        return rid

    def _build_envelope(
        self, method: str, params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Build a JSON-RPC 2.0 request envelope."""
        envelope: dict[str, Any] = {
            "jsonrpc": "2.0",
            "id": self._next_request_id(),
            "method": method,
        }
        if params is not None:
            envelope["params"] = params
        return envelope

    def _build_headers(self) -> dict[str, str]:
        """Build HTTP headers for MCP requests."""
        headers = self._client._auth_headers()
        headers["Content-Type"] = "application/json"
        headers["Accept"] = "application/json"
        return headers

    @staticmethod
    def _parse_response(data: dict[str, Any]) -> Any:
        """Extract the result from a JSON-RPC response, or raise McpError."""
        if "error" in data:
            err = data["error"]
            raise McpError(
                code=err.get("code", -1),
                message=err.get("message", "Unknown MCP error"),
                data=err.get("data"),
            )
        return data.get("result")

    # ── Async RPC ────────────────────────────────────────────────────

    async def _rpc(
        self, method: str, params: dict[str, Any] | None = None,
    ) -> Any:
        """Send a JSON-RPC 2.0 request (async) and return the result.

        Raises :class:`McpError` if the response contains a JSON-RPC error.
        """
        envelope = self._build_envelope(method, params)
        url = self._client.base_url + "/v1/mcp"
        headers = self._build_headers()
        body = json.dumps(envelope).encode()

        if self._client._async_client is None:
            raise RuntimeError("No async client available")
        resp = await self._client._async_client.post(
            url, content=body, headers=headers,
        )
        return self._parse_response(resp.json())

    # ── Sync RPC ─────────────────────────────────────────────────────

    def _rpc_sync(
        self, method: str, params: dict[str, Any] | None = None,
    ) -> Any:
        """Send a JSON-RPC 2.0 request (sync) and return the result.

        Raises :class:`McpError` if the response contains a JSON-RPC error.
        """
        envelope = self._build_envelope(method, params)
        url = self._client.base_url + "/v1/mcp"
        headers = self._build_headers()
        body = json.dumps(envelope).encode()

        if self._client._sync_client is None:
            raise RuntimeError("No sync client available")
        resp = self._client._sync_client.post(
            url, content=body, headers=headers,
        )
        return self._parse_response(resp.json())

    # ── initialize ───────────────────────────────────────────────────

    async def initialize(self) -> McpServerInfo:
        """Send ``initialize`` and return server info.

        Sends ``protocolVersion: "2025-03-26"`` with client identity.
        """
        result = await self._rpc("initialize", {
            "protocolVersion": "2025-03-26",
            "capabilities": {},
            "clientInfo": {"name": "attago-python", "version": VERSION},
        })
        return McpServerInfo.from_dict(result)

    def initialize_sync(self) -> McpServerInfo:
        """Synchronous version of :meth:`initialize`."""
        result = self._rpc_sync("initialize", {
            "protocolVersion": "2025-03-26",
            "capabilities": {},
            "clientInfo": {"name": "attago-python", "version": VERSION},
        })
        return McpServerInfo.from_dict(result)

    # ── tools/list ───────────────────────────────────────────────────

    async def list_tools(self) -> list[McpTool]:
        """List available MCP tools.

        Sends ``tools/list`` and returns a list of tool definitions.
        """
        result = await self._rpc("tools/list")
        return [McpTool.from_dict(t) for t in result.get("tools", [])]

    def list_tools_sync(self) -> list[McpTool]:
        """Synchronous version of :meth:`list_tools`."""
        result = self._rpc_sync("tools/list")
        return [McpTool.from_dict(t) for t in result.get("tools", [])]

    # ── tools/call ───────────────────────────────────────────────────

    async def call_tool(
        self, name: str, arguments: dict[str, Any] | None = None,
    ) -> McpToolCallResult:
        """Call an MCP tool by name.

        Sends ``tools/call`` with the tool name and arguments.
        """
        result = await self._rpc("tools/call", {
            "name": name,
            "arguments": arguments or {},
        })
        return McpToolCallResult.from_dict(result)

    def call_tool_sync(
        self, name: str, arguments: dict[str, Any] | None = None,
    ) -> McpToolCallResult:
        """Synchronous version of :meth:`call_tool`."""
        result = self._rpc_sync("tools/call", {
            "name": name,
            "arguments": arguments or {},
        })
        return McpToolCallResult.from_dict(result)

    # ── ping ─────────────────────────────────────────────────────────

    async def ping(self) -> None:
        """Send a ``ping`` request. Expects empty result."""
        await self._rpc("ping")

    def ping_sync(self) -> None:
        """Synchronous version of :meth:`ping`."""
        self._rpc_sync("ping")
