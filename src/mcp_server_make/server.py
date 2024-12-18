"""MCP Server for GNU Make - Core functionality."""

import argparse
import asyncio
import os
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse, quote, unquote

from pydantic import AnyUrl
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Resource, TextContent, Tool

from .exceptions import MakefileError, SecurityError

# Regular expression for validating Make target names
import re

VALID_TARGET_PATTERN = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_-]*$")


def get_validated_path(base_dir: Path, subpath: Optional[str] = None) -> Path:
    """Validate and resolve a path within project boundaries."""
    try:
        base = base_dir.resolve()
        if subpath is None:
            return base
        requested = (base / subpath).resolve()
        if not str(requested).startswith(str(base)):
            raise SecurityError("Path access denied: outside project boundary")
        return requested
    except Exception as e:
        raise SecurityError(f"Invalid path: {str(e)}")


def get_safe_environment() -> Dict[str, str]:
    """Get a sanitized environment for Make execution."""
    env = os.environ.copy()
    for key in list(env.keys()):
        if key.startswith(("LD_", "DYLD_", "PATH")):
            del env[key]
    return env


def create_make_url(path: str) -> AnyUrl:
    """Create a properly formatted MCP URI."""
    path = path.strip().strip("/")
    uri = f"make://localhost/{quote(path, safe='/')}"
    return AnyUrl(uri)


def normalize_uri_path(uri: AnyUrl) -> str:
    """Normalize a URI path for consistent comparison."""
    parsed = urlparse(str(uri))
    if not parsed.path or parsed.path == "/":
        raise ValueError("URI must have a path component")
    return unquote(parsed.path.strip("/")).lower()


class MakeServer(Server):
    """MCP Server implementation for GNU Make functionality."""

    def __init__(self, makefile_dir: Path | str | None = None):
        """Initialize the Make server."""
        super().__init__("mcp-server-make")
        self.makefile_dir = Path(makefile_dir).resolve() if makefile_dir else Path.cwd()
        if not (self.makefile_dir / "Makefile").exists():
            raise SecurityError(f"No Makefile found in directory: {self.makefile_dir}")

    async def read_makefile(self, path: Path) -> str:
        """Safely read a Makefile's contents."""
        try:
            async with asyncio.Lock():
                return path.read_text()
        except Exception as e:
            raise MakefileError(f"Failed to read Makefile: {str(e)}")

    def validate_makefile_syntax(self, content: str) -> bool:
        """Perform basic Makefile syntax validation."""
        try:
            if not content.strip():
                raise MakefileError("Empty Makefile")
            lines = content.splitlines()
            for i, line in enumerate(lines, 1):
                if line.strip().startswith(".") and ":" not in line:
                    raise MakefileError(f"Invalid directive on line {i}: {line}")
            return True
        except Exception as e:
            raise MakefileError(f"Makefile validation failed: {str(e)}")

    async def parse_makefile_targets(self) -> List[Dict[str, Optional[str]]]:
        """Parse Makefile to extract targets and their metadata."""
        path = get_validated_path(self.makefile_dir, "Makefile")
        content = await self.read_makefile(path)

        targets = []
        current_comment = []
        current_description = None

        for line in content.splitlines():
            line = line.strip()
            if line.startswith("#"):
                current_comment.append(line[1:].strip())
            elif ":" in line and not line.startswith("\t"):
                target = line.split(":", 1)[0].strip()
                description_parts = line.split("##", 1)
                if len(description_parts) > 1:
                    current_description = description_parts[1].strip()
                if VALID_TARGET_PATTERN.match(target):
                    description = (
                        current_description or " ".join(current_comment) or None
                    )
                    targets.append({"name": target, "description": description})
                current_comment = []
                current_description = None
            else:
                current_comment = []
        return targets

    async def _list_resources(self) -> List[Resource]:
        """List available Make-related resources."""
        try:
            resources = []
            makefile_path = get_validated_path(self.makefile_dir, "Makefile")
            if makefile_path.exists():
                resources.append(
                    Resource(
                        uri=create_make_url("current/makefile"),
                        name="Current Makefile",
                        description="Contents of the current Makefile",
                        mimeType="text/plain",
                    )
                )
                targets = await self.parse_makefile_targets()
                if targets:
                    resources.append(
                        Resource(
                            uri=create_make_url("targets"),
                            name="Make Targets",
                            description="List of available Make targets",
                            mimeType="application/json",
                        )
                    )
            return resources
        except Exception as e:
            raise ValueError(f"Failed to list resources: {e}")

    @property
    def list_resources(self) -> Any:
        """List available Make-related resources."""
        return self._list_resources

    async def _read_resource(self, uri: AnyUrl | str) -> str:
        """Read Make-related resource content."""
        try:
            if isinstance(uri, str):
                parsed = urlparse(uri)
                if parsed.scheme != "make":
                    raise ValueError(f"Unsupported URI scheme: {parsed.scheme}")
                uri = create_make_url(uri[7:] if uri.startswith("make://") else uri)

            norm_path = normalize_uri_path(uri)
            if norm_path == "current/makefile":
                file_path = get_validated_path(self.makefile_dir, "Makefile")
                content = await self.read_makefile(file_path)
                self.validate_makefile_syntax(content)
                return content
            elif norm_path == "targets":
                targets = await self.parse_makefile_targets()
                return str(targets)
            raise ValueError(f"Unknown resource path: {norm_path}")
        except (MakefileError, SecurityError) as e:
            raise ValueError(str(e))
        except Exception as e:
            raise ValueError(f"Error reading resource: {str(e)}")

    @property
    def read_resource(self) -> Any:
        """Read Make-related resource content."""
        return self._read_resource

    async def run_make_target(self, target: str, timeout: int) -> str:
        """Run a Make target with safety controls."""
        if not VALID_TARGET_PATTERN.match(target):
            raise ValueError(f"Invalid target name: {target}")

        original_cwd = Path.cwd()
        try:
            # Change to Makefile directory
            os.chdir(str(self.makefile_dir))

            proc = await asyncio.create_subprocess_exec(
                "make",
                target,
                env=get_safe_environment(),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
            if proc.returncode != 0:
                error_msg = stderr.decode().strip()
                raise MakefileError(f"Target execution failed: {error_msg}")
            return stdout.decode()
        except asyncio.TimeoutError:
            raise MakefileError(f"Target execution exceeded {timeout}s timeout")
        finally:
            # Restore original working directory
            os.chdir(str(original_cwd))

    @classmethod
    async def list_tools(cls) -> List[Tool]:
        """List available Make-related tools."""
        return [
            Tool(
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
            Tool(
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

    async def _call_tool(self, name: str, arguments: dict | None) -> list[TextContent]:
        """Execute a Make-related tool."""
        if not arguments:
            raise ValueError("Tool arguments required")

        if name == "list-targets":
            pattern = arguments.get("pattern", "*")
            targets = await self.parse_makefile_targets()
            if pattern != "*":
                try:
                    pattern_re = re.compile(pattern)
                    targets = [t for t in targets if pattern_re.search(t["name"])]
                except re.error:
                    raise ValueError(f"Invalid pattern: {pattern}")
            return [
                TextContent(
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
            output = await self.run_make_target(target, timeout)
            return [TextContent(type="text", text=output)]

        raise ValueError(f"Unknown tool: {name}")

    @property
    def call_tool(self) -> Any:
        """Execute a Make-related tool."""
        return self._call_tool


async def serve(makefile_dir: str | Path | None = None) -> None:
    """Run the Make MCP server."""
    server = MakeServer(makefile_dir=makefile_dir)
    async with stdio_server() as (read_stream, write_stream):
        init_options = server.create_initialization_options()
        await server.run(read_stream, write_stream, init_options, raise_exceptions=True)


async def main() -> None:
    """Run the server using stdin/stdout streams."""
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
