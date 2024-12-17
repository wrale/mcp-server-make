"""MCP Server for GNU Make - Core functionality."""

import asyncio

from mcp.server import NotificationOptions, Server
import mcp.server.stdio
from mcp.server.models import InitializationOptions

from . import handlers

# Initialize the MCP server instance
server = Server("mcp-server-make")

# Register handlers
server.list_resources(handlers.handle_list_resources)
server.read_resource(handlers.handle_read_resource)
server.list_tools(handlers.handle_list_tools)
server.call_tool(handlers.handle_call_tool)


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
