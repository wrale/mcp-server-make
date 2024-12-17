"""MCP Server for GNU Make - Core functionality."""

import asyncio
from typing import Any, List

from pydantic import AnyUrl
from mcp.server import (
    NotificationOptions,
    Server,
)
import mcp.server.stdio
import mcp.types as types
from mcp.server.models import InitializationOptions

from . import handlers


class MakeServer(Server):
    """MCP Server implementation for GNU Make functionality."""

    def __init__(self):
        """Initialize the Make server."""
        super().__init__("mcp-server-make")
        self._init_handlers()

    def _init_handlers(self) -> None:
        """Initialize the handler functions."""

        async def _list_resources() -> List[types.Resource]:
            try:
                return await handlers.handle_list_resources()
            except Exception as e:
                raise ValueError(str(e))

        async def _read_resource(uri: AnyUrl | str) -> str:
            try:
                # Convert string URIs to AnyUrl instances
                if isinstance(uri, str):
                    uri = handlers.create_make_url(uri.removeprefix("make://"))
                return await handlers.handle_read_resource(uri)
            except Exception as e:
                raise ValueError(str(e))

        async def _list_tools() -> List[types.Tool]:
            try:
                return await handlers.handle_list_tools()
            except Exception as e:
                raise ValueError(str(e))

        async def _call_tool(
            name: str,
            arguments: dict | None,
        ) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
            try:
                return await handlers.handle_call_tool(name, arguments)
            except Exception as e:
                raise ValueError(str(e))

        self._list_resources_handler = _list_resources
        self._read_resource_handler = _read_resource
        self._list_tools_handler = _list_tools
        self._call_tool_handler = _call_tool

    @property
    def list_resources(self) -> Any:
        """Return list_resources handler."""
        return self._list_resources_handler

    @property
    def read_resource(self) -> Any:
        """Return read_resource handler."""
        return self._read_resource_handler

    @property
    def list_tools(self) -> Any:
        """Return list_tools handler."""
        return self._list_tools_handler

    @property
    def call_tool(self) -> Any:
        """Return call_tool handler."""
        return self._call_tool_handler


# Create the singleton server instance
server = MakeServer()


async def main():
    """Run the server using stdin/stdout streams."""
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        init_options = InitializationOptions(
            server_name="mcp-server-make",
            server_version="0.1.0",
            capabilities=server.get_capabilities(
                notification_options=NotificationOptions(),
                experimental_capabilities={},
            ),
        )
        await server.run(read_stream, write_stream, init_options)


if __name__ == "__main__":
    asyncio.run(main())
