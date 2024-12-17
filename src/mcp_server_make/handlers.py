"""MCP protocol handlers for Make server functionality."""

import re
from typing import List, Optional

from pydantic import AnyUrl
import mcp.types as types
from yarl import URL

from .exceptions import MakefileError, SecurityError
from .execution import ExecutionManager
from .make import parse_makefile_targets
from .security import get_validated_path


def create_mcp_url(path: str) -> str:
    """Create a properly formatted MCP URI string."""
    return str(URL.build(scheme="make", path=path))


async def handle_list_resources() -> list[types.Resource]:
    """List available Make-related resources."""
    resources = []

    try:
        # Add Makefile resource
        makefile_path = get_validated_path() / "Makefile"
        if makefile_path.exists():
            resources.append(
                types.Resource(
                    uri=create_mcp_url("/current/makefile"),
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
                    uri=create_mcp_url("/targets"),
                    name="Make Targets",
                    description="List of available Make targets",
                    mimeType="application/json",
                )
            )

    except Exception as e:
        # Log error but continue - we want partial results if possible
        print(f"Error listing resources: {e}")

    return resources


async def handle_read_resource(uri: AnyUrl) -> str:
    """
    Read Make-related resource content.

    Args:
        uri: Resource URI to read

    Returns:
        Resource content
    """
    from .make import read_makefile, validate_makefile_syntax

    # Convert AnyUrl to URL for proper parsing
    url = URL(str(uri))

    if url.scheme != "make":
        raise ValueError(f"Unsupported URI scheme: {url.scheme}")

    try:
        if url.path == "/current/makefile":
            path = get_validated_path() / "Makefile"
            content = await read_makefile(path)
            validate_makefile_syntax(content)
            return content

        elif url.path == "/targets":
            targets = await parse_makefile_targets()
            return str(targets)  # Basic string representation for now

        raise ValueError(f"Unknown resource path: {url.path}")

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
