"""MCP server implementation for make functionality."""

from typing import Any, Dict, List, Optional, cast
import os
import asyncio
from asyncio import StreamReader
from subprocess import PIPE
import sys

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

    target: str = Field(description="Make target to run")


async def serve(
    make_path: Optional[str] = None, working_dir: Optional[str] = None
) -> None:
    """Run the make MCP server.

    Args:
        make_path: Optional path to Makefile
        working_dir: Optional working directory

    Raises:
        McpError: If the Makefile cannot be found at the specified path
        Exception: For other unexpected errors during server operation
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
    async def list_tools() -> List[Tool]:
        """List available tools.

        Returns:
            List of available tools, currently only the make tool.
        """
        return [
            Tool(
                name="make",
                description="Run a make target from the Makefile",
                inputSchema=Make.model_json_schema(),
            )
        ]

    @server.call_tool()
    async def call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
        """Execute a tool.

        Args:
            name: Name of the tool to execute
            arguments: Arguments for the tool

        Returns:
            List of text content with tool execution results
        """
        if name != "make":
            return [TextContent(type="text", text=f"Unknown tool: {name}")]

        try:
            args = Make(**arguments)
        except Exception as e:
            return [TextContent(type="text", text=f"Invalid arguments: {str(e)}")]

        proc = None
        try:
            # Run make command
            proc = await asyncio.create_subprocess_exec(
                "make",
                "-f",
                make_path,
                args.target,
                stdout=PIPE,
                stderr=PIPE,
                # Ensure proper error propagation from child process
                start_new_session=True,
            )
        except Exception as e:
            return [
                TextContent(type="text", text=f"Failed to start make process: {str(e)}")
            ]

        try:
            stdout_data = bytearray()
            stderr_data = bytearray()

            async def read_stream(stream: StreamReader, buffer: bytearray) -> None:
                while True:
                    chunk = await stream.read(8192)
                    if not chunk:
                        break
                    buffer.extend(chunk)

            # Create tasks manually for better type safety
            tasks = [
                asyncio.create_task(
                    read_stream(cast(StreamReader, proc.stdout), stdout_data)
                ),
                asyncio.create_task(
                    read_stream(cast(StreamReader, proc.stderr), stderr_data)
                ),
                asyncio.create_task(proc.wait()),
            ]

            # Wait for all tasks to complete
            await asyncio.gather(*tasks)

            stderr_text = stderr_data.decode() if stderr_data else ""
            stdout_text = stdout_data.decode() if stdout_data else ""

        except asyncio.CancelledError:
            # Handle cancellation by cleaning up the subprocess
            if proc and proc.returncode is None:
                try:
                    proc.terminate()
                    await asyncio.sleep(0.1)
                    if proc.returncode is None:
                        proc.kill()
                except Exception:
                    pass

            # Cancel any remaining tasks
            for task in tasks:
                if not task.done():
                    task.cancel()

            raise

        except Exception as e:
            error_lines = [str(e)]
            if hasattr(e, "__context__") and e.__context__:
                error_lines.append(f"Caused by: {str(e.__context__)}")
            error_msg = "\n".join(error_lines)

            return [
                TextContent(
                    type="text", text=f"Error during make execution: {error_msg}"
                )
            ]

        if proc.returncode != 0:
            return [
                TextContent(
                    type="text",
                    text=f"Make failed with exit code {proc.returncode}:\n{stderr_text}\n{stdout_text}",
                )
            ]

        return [TextContent(type="text", text=stdout_text)]

    @server.list_prompts()
    async def list_prompts() -> List[Prompt]:
        """List available prompts.

        Returns:
            Empty list as no prompts are currently supported.
        """
        return []

    @server.get_prompt()
    async def get_prompt(
        name: str, arguments: Optional[Dict[str, Any]]
    ) -> GetPromptResult:
        """Get a prompt by name.

        Args:
            name: Name of the prompt
            arguments: Optional arguments for the prompt

        Raises:
            McpError: Always raises as no prompts are currently supported
        """
        raise McpError(INVALID_PARAMS, f"Unknown prompt: {name}")

    try:
        options = server.create_initialization_options()
        async with stdio_server() as streams:
            read_stream, write_stream = streams
            await server.run(read_stream, write_stream, options, raise_exceptions=True)
    except Exception as e:
        print(f"Server error: {str(e)}", file=sys.stderr)
        # Use a clean exit to avoid unhandled exception messages
        sys.exit(1)
