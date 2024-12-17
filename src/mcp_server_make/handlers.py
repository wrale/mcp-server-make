"""MCP protocol handlers for Make server functionality."""

import re
from typing import List, Optional
from urllib.parse import quote

from pydantic import AnyUrl
import mcp.types as types

from .exceptions import MakefileError, SecurityError
from .execution import ExecutionManager
from .make import parse_makefile_targets
from .security import get_validated_path


def create_make_url(path: str) -> AnyUrl:
    """Create a properly formatted MCP URI for the Make server.

    Args:
        path: Path without scheme (e.g. "current/makefile" or "targets")

    Returns:
        AnyUrl for Make server (e.g. "make://current/makefile")
    """
    # Remove any leading/trailing slashes and encode path
    clean_path = path.strip("/")
    safe_path = quote(clean_path, safe="/")

    # Build URI with proper host and path
    return AnyUrl(f"make://{safe_path}")


async def handle_list_resources() -> list[types.Resource]:
    """List available Make-related resources."""
    resources = []

    try:
        # Add Makefile resource
        makefile_path = get_validated_path() / "Makefile"
        if makefile_path.exists():
            resources.append(
                types.Resource(
                    uri=create_make_url("current/makefile"),
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
                    uri=create_make_url("targets"),
                    name="Make Targets",
                    description="List of available Make targets",
                    mimeType="application/json",
                )
            )

    except Exception as e:
        print(f"Error listing resources: {e}")

    return resources


async def handle_read_resource(uri: AnyUrl) -> str:
    """Read Make-related resource content.

    Args:
        uri: Resource URI to read (e.g. "make://current/makefile")

    Returns:
        Resource content as string

    Raises:
        ValueError: If URI is invalid or resource not found
    """
    from .make import read_makefile, validate_makefile_syntax

    if uri.scheme != "make":
        raise ValueError(f"Unsupported URI scheme: {uri.scheme}")

    # Ensure path exists and convert to string for safe handling
    if not uri.path:
        raise ValueError("URI must have a path component")
    path_str = str(uri.path)

    # Strip any extra slashes and host parts from path
    norm_path = "/".join(p for p in path_str.split("/") if p)
    norm_path = norm_path.lower()

    try:
        if norm_path == "current/makefile":
            file_path = get_validated_path() / "Makefile"
            content = await read_makefile(file_path)
            validate_makefile_syntax(content)
            return content

        elif norm_path == "targets":
            targets = await parse_makefile_targets()
            return str(targets)

        raise ValueError(f"Unknown resource path: {norm_path}")

    except (MakefileError, SecurityError) as e:
        raise ValueError(str(e))
    except Exception as e:
        raise ValueError(f"Error reading resource: {str(e)}")


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
    name: str, arguments: Optional[dict]
) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
    """Execute a Make-related tool.

    Args:
        name: Tool name to execute
        arguments: Optional tool arguments

    Returns:
        List of tool result content

    Raises:
        ValueError: If tool not found or invalid arguments
    """
    if not arguments:
        raise ValueError("Tool arguments required")

    if name == "list-targets":
        pattern = arguments.get("pattern", "*")
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
        if "target" not in arguments:
            raise ValueError("Target name required")

        target = arguments["target"]
        timeout = min(int(arguments.get("timeout", 300)), 3600)

        try:
            async with ExecutionManager(timeout=timeout) as mgr:
                output = await mgr.run_target(target)
                return [types.TextContent(type="text", text=output)]
        except (MakefileError, SecurityError) as e:
            raise ValueError(str(e))

    raise ValueError(f"Unknown tool: {name}")
