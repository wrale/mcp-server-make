"""MCP Server for GNU Make - Core functionality."""

import asyncio
from typing import List

from pydantic import AnyUrl
from mcp.server import NotificationOptions, Server
import mcp.server.stdio
import mcp.types as types
from mcp.server.models import InitializationOptions

from . import handlers


class MakeServer(Server):
    """MCP Server implementation for GNU Make functionality."""

    def __init__(self):
        """Initialize the Make server."""
        super().__init__("mcp-server-make")

    async def list_resources(self) -> List[types.Resource]:
        """Handle list resources request."""
        try:
            return await handlers.handle_list_resources()
        except Exception as e:
            await self.request_context.session.send_log_message(
                level="error",
                data=f"Error listing resources: {str(e)}",
            )
            raise

    async def read_resource(self, uri: AnyUrl) -> str:
        """Handle read resource request."""
        try:
            return await handlers.handle_read_resource(uri)
        except Exception as e:
            await self.request_context.session.send_log_message(
                level="error",
                data=f"Error reading resource {uri}: {str(e)}",
            )
            raise

    async def list_tools(self) -> List[types.Tool]:
        """Handle list tools request."""
        return await handlers.handle_list_tools()

    async def call_tool(
        self, name: str, arguments: dict | None
    ) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
        """Handle tool execution request."""
        return await handlers.handle_call_tool(name, arguments)


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
