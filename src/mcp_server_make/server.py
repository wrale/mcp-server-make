"""MCP Server for GNU Make - Core functionality."""

import argparse
import asyncio
from pathlib import Path
from typing import List
from urllib.parse import urlparse

from pydantic import AnyUrl
from mcp.server import Server
import mcp.server.stdio
import mcp.types as types

from . import handlers
from .exceptions import SecurityError
from .execution import ExecutionManager
from .make import parse_makefile_targets


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

    async def list_resources(self) -> List[types.Resource]:
        """List available Make-related resources."""
        try:
            resources = await handlers.handle_list_resources(self.makefile_dir)
            return resources
        except Exception as e:
            raise ValueError(f"Failed to list resources: {e}")

    async def read_resource(self, uri: AnyUrl | str) -> str:
        """Read Make-related resource content."""
        try:
            # Convert string URIs to AnyUrl
            if isinstance(uri, str):
                parsed = urlparse(uri)
                if parsed.scheme != "make":
                    raise ValueError(f"Unsupported URI scheme: {parsed.scheme}")
                uri = handlers.create_make_url(
                    uri[7:] if uri.startswith("make://") else uri
                )

            return await handlers.handle_read_resource(uri, self.makefile_dir)
        except Exception as e:
            raise ValueError(f"Failed to read resource: {e}")

    @classmethod
    async def list_tools(cls) -> List[types.Tool]:
        """List available Make-related tools.

        Returns:
            List of available tools
        """
        return [
            types.Tool(
                name="list-targets",
                description="List available Make targets",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "pattern": {
                            "type": "string",
                            "description": "Optional filter pattern",
                        }
                    },
                },
            ),
            types.Tool(
                name="run-target",
                description="Execute a Make target",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "target": {
                            "type": "string",
                            "description": "Target to execute",
                        },
                        "timeout": {
                            "type": "integer",
                            "minimum": 1,
                            "maximum": 3600,
                            "default": 300,
                            "description": "Maximum execution time in seconds",
                        },
                    },
                    "required": ["target"],
                },
            ),
        ]

    async def call_tool(
        self, name: str, arguments: dict | None
    ) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
        """Execute a Make-related tool."""
        if not arguments:
            raise ValueError("Tool arguments required")

        if name == "list-targets":
            target_list = await parse_makefile_targets(self.makefile_dir)
            return [
                types.TextContent(
                    type="text",
                    text="\n".join(
                        f"{t['name']}: {t['description'] or 'No description'}"
                        for t in target_list
                    ),
                )
            ]

        elif name == "run-target":
            if "target" not in arguments:
                raise ValueError("Target name required")

            target = arguments["target"]
            timeout = min(int(arguments.get("timeout", 300)), 3600)

            async with ExecutionManager(
                base_dir=self.makefile_dir, timeout=timeout
            ) as mgr:
                output = await mgr.run_target(target)
                return [types.TextContent(type="text", text=output)]

        raise ValueError(f"Unknown tool: {name}")


async def serve(makefile_dir: str | Path | None = None) -> None:
    """Run the Make MCP server.

    Args:
        makefile_dir: Optional directory containing Makefile to manage
    """
    server = MakeServer(makefile_dir=makefile_dir)

    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        init_options = server.create_initialization_options()
        await server.run(read_stream, write_stream, init_options, raise_exceptions=True)


async def main() -> None:
    """Run the server using stdin/stdout streams."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="MCP Server for GNU Make")
    parser.add_argument(
        "--makefile-dir",
        type=str,
        help="Directory containing the Makefile to manage",
    )
    args = parser.parse_args()

    await serve(makefile_dir=args.makefile_dir)


if __name__ == "__main__":
    asyncio.run(main())
