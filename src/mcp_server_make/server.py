"""MCP Server for GNU Make - Core functionality."""

import argparse
import asyncio
from pathlib import Path
from typing import Any, List
from urllib.parse import urlparse

from pydantic import AnyUrl
from mcp.server import (
    NotificationOptions,
    Server,
)
import mcp.server.stdio
import mcp.types as types
from mcp.server.models import InitializationOptions

from . import handlers
from .exceptions import SecurityError


class MakeServer(Server):
    """MCP Server implementation for GNU Make functionality."""

    def __init__(self, makefile_dir: Path | str | None = None):
        """Initialize the Make server.

        Args:
            makefile_dir: Directory containing the Makefile to manage
        """
        super().__init__("mcp-server-make")

        # Resolve and validate the Makefile directory
        self.makefile_dir = Path(makefile_dir).resolve() if makefile_dir else Path.cwd()
        if not (self.makefile_dir / "Makefile").exists():
            raise SecurityError(f"No Makefile found in directory: {self.makefile_dir}")

        self._init_handlers()

    def _init_handlers(self) -> None:
        """Initialize the handler functions."""

        async def _list_resources() -> List[types.Resource]:
            try:
                return await handlers.handle_list_resources(self.makefile_dir)
            except Exception as e:
                raise ValueError(str(e))

        async def _read_resource(uri: AnyUrl | str) -> str:
            try:
                # Handle invalid URI scheme early
                if isinstance(uri, str):
                    parsed = urlparse(uri)
                    if parsed.scheme != "make":
                        raise ValueError(f"Unsupported URI scheme: {parsed.scheme}")
                    # Only remove prefix if it's the make:// scheme
                    uri = handlers.create_make_url(
                        uri[7:] if uri.startswith("make://") else uri
                    )

                return await handlers.handle_read_resource(uri, self.makefile_dir)
            except ValueError as e:
                # Preserve original error messages
                raise ValueError(str(e))
            except Exception as e:
                raise ValueError(f"Failed to read resource: {str(e)}")

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
                return await handlers.handle_call_tool(
                    name, arguments, self.makefile_dir
                )
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


async def main():
    """Run the server using stdin/stdout streams."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="MCP Server for GNU Make")
    parser.add_argument(
        "--makefile-dir",
        type=str,
        help="Directory containing the Makefile to manage",
    )
    args = parser.parse_args()

    # Create server instance with configured directory
    server = MakeServer(makefile_dir=args.makefile_dir)

    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        init_options = InitializationOptions(
            server_name="mcp-server-make",
            server_version="0.1.5",
            capabilities=server.get_capabilities(
                notification_options=NotificationOptions(),
                experimental_capabilities={},
            ),
        )
        await server.run(read_stream, write_stream, init_options)


if __name__ == "__main__":
    asyncio.run(main())
