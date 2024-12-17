"""MCP protocol handlers for Make server functionality."""

import re
from typing import List

from pydantic import AnyUrl
import mcp.types as types

from .exceptions import MakefileError, SecurityError
from .execution import ExecutionManager
from .make import parse_makefile_targets
from .security import get_validated_path


async def handle_list_resources(server) -> list[types.Resource]:
    """List available Make-related resources."""
    resources = []

    try:
        # Add Makefile resource
        makefile_path = get_validated_path() / "Makefile"
        if makefile_path.exists():
            resources.append(
                types.Resource(
                    uri="make://current/makefile",
                    name="Current Makefile",
                    description="Contents of the current Makefile",
                    mimeType="text/plain",
                )
            )

        # Add targets resource
        targets = await parse_makefile_targets()
        if targets:
            resources.append(
                types.Resource(
                    uri="make://targets",
                    name="Make Targets",
                    description="List of available Make targets",
                    mimeType="application/json",
                )
            )

    except Exception as e:
        await server.request_context.session.send_log_message(
            level="error", data=f"Error listing resources: {str(e)}"
        )

    return resources


async def handle_read_resource(uri: str) -> str:
    """
    Read Make-related resource content.

    Args:
        uri: Resource URI to read

    Returns:
        Resource content
    """
    from .make import read_makefile, validate_makefile_syntax

    parsed_uri = AnyUrl(uri)
    if parsed_uri.scheme != "make":
        raise ValueError(f"Unsupported URI scheme: {parsed_uri.scheme}")

    try:
        if parsed_uri.path == "/current/makefile":
            path = get_validated_path() / "Makefile"
            content = await read_makefile(path)
            validate_makefile_syntax(content)
            return content

        elif parsed_uri.path == "/targets":
            targets = await parse_makefile_targets()
            return str(targets)  # Basic string representation for now

        raise ValueError(f"Unknown resource path: {parsed_uri.path}")

    except (MakefileError, SecurityError) as e:
        raise ValueError(str(e))


async def handle_list_tools() -> List[types.Tool]:
    """List available Make-related tools."""
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
                    "target": {"type": "string", "description": "Target to execute"},
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


async def handle_call_tool(
    name: str, arguments: dict | None
) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
    """Handle Make-related tool execution."""
    if name == "list-targets":
        pattern = (arguments or {}).get("pattern", "*")
        targets = await parse_makefile_targets()

        # Apply pattern filtering if specified
        if pattern != "*":
            try:
                pattern_re = re.compile(pattern)
                targets = [t for t in targets if pattern_re.search(t["name"])]
            except re.error:
                raise ValueError(f"Invalid pattern: {pattern}")

        return [
            types.TextContent(
                type="text",
                text="\n".join(
                    f"{t['name']}: {t['description'] or 'No description'}"
                    for t in targets
                ),
            )
        ]

    elif name == "run-target":
        if not arguments or "target" not in arguments:
            raise ValueError("Target name required")

        target = arguments["target"]
        timeout = min(int(arguments.get("timeout", 300)), 3600)

        try:
            async with ExecutionManager(timeout=timeout) as mgr:
                output = await mgr.run_target(target)
                return [types.TextContent(type="text", text=output)]
        except (MakefileError, SecurityError) as e:
            raise ValueError(str(e))

    else:
        raise ValueError(f"Unknown tool: {name}")
