"""MCP Server for GNU Make - Core functionality."""

import asyncio
from typing import List

from pydantic import AnyUrl
from mcp.server import NotificationOptions, Server
import mcp.server.stdio
import mcp.types as types
from mcp.server.models import InitializationOptions

from . import handlers


# Initialize server instance
server = Server(
    "mcp-server-make",
    capabilities={
        "list_resources": True,
        "read_resource": True,
        "list_tools": True,
        "call_tool": True,
    },
)


@server.on_list_resources
async def handle_list_resources() -> List[types.Resource]:
    """Handle list resources request."""
    try:
        return await handlers.handle_list_resources()
    except Exception as e:
        await server.request_context.session.send_log_message(
            level="error",
            data=f"Error listing resources: {str(e)}",
        )
        raise


@server.on_read_resource
async def handle_read_resource(uri: AnyUrl) -> str:
    """Handle read resource request."""
    try:
        return await handlers.handle_read_resource(uri)
    except Exception as e:
        await server.request_context.session.send_log_message(
            level="error",
            data=f"Error reading resource {uri}: {str(e)}",
        )
        raise


@server.on_list_tools
async def handle_list_tools() -> List[types.Tool]:
    """Handle list tools request."""
    return await handlers.handle_list_tools()


@server.on_call_tool
async def handle_call_tool(
    name: str, arguments: dict | None
) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
    """Handle tool execution request."""
    return await handlers.handle_call_tool(name, arguments)


async def main():
    """Run the server using stdin/stdout streams."""
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="mcp-server-make",
                server_version="0.1.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )


if __name__ == "__main__":
    asyncio.run(main())
