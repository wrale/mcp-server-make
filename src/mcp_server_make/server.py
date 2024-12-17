"""MCP Server for GNU Make - Core functionality."""

import asyncio
import os
import re
from pathlib import Path
from typing import List, Optional

from mcp.server.models import InitializationOptions
from mcp.server import NotificationOptions, Server
import mcp.server.stdio
import mcp.types as types
from pydantic import AnyUrl


class MakefileError(Exception):
    """Raised when there are issues with Makefile operations."""

    pass


class SecurityError(Exception):
    """Raised for security-related violations."""

    pass


# Regular expression for validating Make target names
VALID_TARGET_PATTERN = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_-]*$")

server = Server("mcp-server-make")


def get_validated_path(path: Optional[str] = None) -> Path:
    """
    Validate and resolve a path within project boundaries.

    Args:
        path: Optional path to validate. Uses current directory if None.

    Returns:
        Resolved Path object

    Raises:
        SecurityError: If path validation fails
    """
    try:
        base_path = Path.cwd() if path is None else Path(path)
        resolved = base_path.resolve()

        # Ensure path is within current directory tree
        if not str(resolved).startswith(str(Path.cwd())):
            raise SecurityError("Path access denied: outside project boundary")

        return resolved
    except Exception as e:
        raise SecurityError(f"Invalid path: {str(e)}")


async def read_makefile(path: Path) -> str:
    """
    Safely read a Makefile's contents.

    Args:
        path: Path to the Makefile

    Returns:
        Contents of the Makefile as string
    """
    try:
        async with asyncio.Lock():  # Ensure thread-safe file access
            return path.read_text()
    except Exception as e:
        raise MakefileError(f"Failed to read Makefile: {str(e)}")


def validate_makefile_syntax(content: str) -> bool:
    """
    Perform basic Makefile syntax validation.

    Args:
        content: Makefile content to validate

    Returns:
        True if validation passes

    Raises:
        MakefileError: If validation fails
    """
    try:
        # Basic syntax checks (can be expanded)
        if not content.strip():
            raise MakefileError("Empty Makefile")

        # Check for basic format validity
        lines = content.splitlines()
        for i, line in enumerate(lines, 1):
            if line.strip().startswith(".") and ":" not in line:
                raise MakefileError(f"Invalid directive on line {i}: {line}")

        return True
    except Exception as e:
        raise MakefileError(f"Makefile validation failed: {str(e)}")


async def parse_makefile_targets() -> List[dict]:
    """
    Parse Makefile to extract targets and their metadata.

    Returns:
        List of target dictionaries with metadata
    """
    path = get_validated_path() / "Makefile"
    content = await read_makefile(path)

    targets = []
    current_comment = []

    for line in content.splitlines():
        line = line.strip()

        if line.startswith("#"):
            current_comment.append(line[1:].strip())
        elif ":" in line and not line.startswith("\t"):
            target = line.split(":", 1)[0].strip()
            if VALID_TARGET_PATTERN.match(target):
                targets.append(
                    {
                        "name": target,
                        "description": " ".join(current_comment)
                        if current_comment
                        else None,
                    }
                )
            current_comment = []
        else:
            current_comment = []

    return targets


class ExecutionManager:
    """Manage Make target execution with safety controls."""

    def __init__(self, timeout: int = 300):
        self.timeout = timeout
        self.start_time = 0

    async def __aenter__(self):
        self.start_time = asyncio.get_event_loop().time()
        return self

    def get_safe_environment(self) -> dict:
        """Get a sanitized environment for Make execution."""
        env = os.environ.copy()
        # Remove potentially dangerous variables
        for key in list(env.keys()):
            if key.startswith(("LD_", "DYLD_", "PATH")):
                del env[key]
        return env

    async def run_target(self, target: str) -> str:
        """
        Run a Make target with safety controls.

        Args:
            target: Name of the target to run

        Returns:
            Command output as string
        """
        if not VALID_TARGET_PATTERN.match(target):
            raise ValueError(f"Invalid target name: {target}")

        env = self.get_safe_environment()

        try:
            proc = await asyncio.create_subprocess_exec(
                "make",
                target,
                env=env,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout, stderr = await asyncio.wait_for(
                proc.communicate(), timeout=self.timeout
            )

            if proc.returncode != 0:
                error_msg = stderr.decode().strip()
                raise MakefileError(f"Target execution failed: {error_msg}")

            return stdout.decode()

        except asyncio.TimeoutError:
            raise MakefileError(f"Target execution exceeded {self.timeout}s timeout")

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass


@server.list_resources()
async def handle_list_resources() -> list[types.Resource]:
    """List available Make-related resources."""
    resources = []

    try:
        # Add Makefile resource
        makefile_path = get_validated_path() / "Makefile"
        if makefile_path.exists():
            resources.append(
                types.Resource(
                    uri=AnyUrl("make://current/makefile"),
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
                    uri=AnyUrl("make://targets"),
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


@server.read_resource()
async def handle_read_resource(uri: AnyUrl) -> str:
    """
    Read Make-related resource content.

    Args:
        uri: Resource URI to read

    Returns:
        Resource content
    """
    if uri.scheme != "make":
        raise ValueError(f"Unsupported URI scheme: {uri.scheme}")

    try:
        if uri.path == "/current/makefile":
            path = get_validated_path() / "Makefile"
            content = await read_makefile(path)
            validate_makefile_syntax(content)
            return content

        elif uri.path == "/targets":
            targets = await parse_makefile_targets()
            return str(targets)  # Basic string representation for now

        raise ValueError(f"Unknown resource path: {uri.path}")

    except (MakefileError, SecurityError) as e:
        raise ValueError(str(e))


@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
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


@server.call_tool()
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
