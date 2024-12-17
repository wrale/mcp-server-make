"""MCP Server for GNU Make - Core functionality."""

import asyncio
import contextvars
from typing import Any, Protocol, List

from pydantic import AnyUrl
from mcp.server import (
    NotificationOptions,
    Server,
    RequestContext,
    ServerSession,
)
import mcp.server.stdio
import mcp.types as types
from mcp.server.models import InitializationOptions

from . import handlers

# Context variable for request handling
request_context: contextvars.ContextVar[RequestContext[ServerSession]] = (
    contextvars.ContextVar("request_context")
)


class ResourceHandlers(Protocol):
    """Protocol defining expected signatures for resource handlers."""

    async def list_resources(self) -> List[types.Resource]:
        """List available resources."""
        ...

    async def read_resource(self, uri: AnyUrl) -> str:
        """Read resource content."""
        ...


class ToolHandlers(Protocol):
    """Protocol defining expected signatures for tool handlers."""

    async def list_tools(self) -> List[types.Tool]:
        """List available tools."""
        ...

    async def call_tool(
        self, name: str, arguments: dict | None
    ) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
        """Execute a tool."""
        ...


class MakeServer(Server):
    """MCP Server implementation for GNU Make functionality."""

    def __init__(self):
        """Initialize the Make server."""
        super().__init__("mcp-server-make")
        self._init_handlers()

    def _init_handlers(self) -> None:
        """Initialize the handler functions."""

        async def _with_context(
            context: RequestContext[ServerSession], func: Any, *args, **kwargs
        ) -> Any:
            """Run a handler function with the request context."""
            token = request_context.set(context)
            try:
                return await func(*args, **kwargs)
            finally:
                request_context.reset(token)

        async def _list_resources() -> List[types.Resource]:
            try:
                return await _with_context(
                    self.request_context, handlers.handle_list_resources
                )
            except Exception as e:
                await self.request_context.session.send_log_message(
                    level="error",
                    data=f"Error listing resources: {str(e)}",
                )
                raise

        async def _read_resource(uri: AnyUrl) -> str:
            try:
                return await _with_context(
                    self.request_context, handlers.handle_read_resource, uri
                )
            except Exception as e:
                await self.request_context.session.send_log_message(
                    level="error",
                    data=f"Error reading resource {uri}: {str(e)}",
                )
                raise

        async def _list_tools() -> List[types.Tool]:
            return await _with_context(self.request_context, handlers.handle_list_tools)

        async def _call_tool(
            name: str, arguments: dict | None
        ) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
            return await _with_context(
                self.request_context, handlers.handle_call_tool, name, arguments
            )

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
