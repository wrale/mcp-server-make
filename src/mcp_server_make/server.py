from typing import Annotated, Optional
import os
import asyncio
from subprocess import PIPE

from mcp.shared.exceptions import McpError
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import (
    GetPromptResult,
    Prompt,
    TextContent,
    Tool,
    INVALID_PARAMS,
)
from pydantic import BaseModel, Field


class Make(BaseModel):
    """Parameters for running make."""

    target: Annotated[
        str,
        Field(
            description="Make target to run",
        ),
    ]


async def serve(
    make_path: Optional[str] = None, working_dir: Optional[str] = None
) -> None:
    """Run the make MCP server.

    Args:
        make_path: Optional path to Makefile
        working_dir: Optional working directory
    """
    server = Server("mcp-make")

    # Set working directory
    if working_dir:
        os.chdir(working_dir)

    # Set make path
    make_path = make_path or "Makefile"
    if not os.path.exists(make_path):
        raise McpError(INVALID_PARAMS, f"Makefile not found at {make_path}")

    @server.list_tools()
    async def list_tools() -> list[Tool]:
        return [
            Tool(
                name="make",
                description="""Run a make target from the Makefile""",
                inputSchema=Make.model_json_schema(),
            )
        ]

    @server.call_tool()
    async def call_tool(name: str, arguments: dict) -> list[TextContent]:
        if name != "make":
            raise McpError(INVALID_PARAMS, f"Unknown tool: {name}")

        try:
            args = Make(**arguments)
        except Exception as e:
            raise McpError(INVALID_PARAMS, str(e))

        # Run make command
        proc = await asyncio.create_subprocess_exec(
            "make", "-f", make_path, args.target, stdout=PIPE, stderr=PIPE
        )
        stdout, stderr = await proc.communicate()

        if proc.returncode != 0:
            return [
                TextContent(
                    type="text", text=f"Make failed with error: {stderr.decode()}"
                )
            ]

        return [TextContent(type="text", text=stdout.decode())]

    @server.list_prompts()
    async def list_prompts() -> list[Prompt]:
        return []

    @server.get_prompt()
    async def get_prompt(name: str, arguments: dict | None) -> GetPromptResult:
        raise McpError(INVALID_PARAMS, f"Unknown prompt: {name}")

    options = server.create_initialization_options()
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, options, raise_exceptions=True)
