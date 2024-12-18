"""MCP server implementation for make functionality."""

from typing import Any, Dict, List, Optional
import os
import asyncio
import logging
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

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


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
        logger.info(f"Changed working directory to: {working_dir}")

    # Set make path
    make_path = make_path or "Makefile"
    if not os.path.exists(make_path):
        logger.error(f"Makefile not found at: {make_path}")
        raise McpError(INVALID_PARAMS, f"Makefile not found at {make_path}")

    logger.info(f"Using Makefile at: {make_path}")

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

        Raises:
            McpError: If the tool is unknown or arguments are invalid
        """
        if name != "make":
            logger.error(f"Unknown tool requested: {name}")
            raise McpError(INVALID_PARAMS, f"Unknown tool: {name}")

        try:
            args = Make(**arguments)
        except Exception as e:
            logger.error(f"Invalid arguments for make tool: {str(e)}")
            raise McpError(INVALID_PARAMS, str(e))

        logger.info(f"Running make target: {args.target}")

        try:
            # Run make command with timeout
            proc = await asyncio.create_subprocess_exec(
                "make", "-f", make_path, args.target, stdout=PIPE, stderr=PIPE
            )

            try:
                stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=300)
            except asyncio.TimeoutError:
                try:
                    proc.terminate()
                    await proc.wait()
                except Exception as e:
                    logger.error(f"Error terminating make process: {e}")
                logger.error("Make command timed out after 300 seconds")
                return [
                    TextContent(
                        type="text", text="Make command timed out after 300 seconds"
                    )
                ]

            if proc.returncode != 0:
                error_msg = stderr.decode() if stderr else "Unknown error occurred"
                logger.error(f"Make command failed: {error_msg}")
                # Format the error message to be more readable
                formatted_error = (
                    f"Make failed with exit code {proc.returncode}:\n{error_msg}"
                )
                return [TextContent(type="text", text=formatted_error)]

            output = stdout.decode()
            logger.info(
                f"Make command completed successfully for target: {args.target}"
            )
            return [TextContent(type="text", text=output)]

        except FileNotFoundError as e:
            logger.error(f"Make executable not found: {e}")
            return [
                TextContent(
                    type="text", text="Make command failed: make executable not found"
                )
            ]
        except Exception as e:
            logger.error(f"Unexpected error running make: {str(e)}")
            return [TextContent(type="text", text=f"Make command failed: {str(e)}")]

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
        logger.error(f"Unknown prompt requested: {name}")
        raise McpError(INVALID_PARAMS, f"Unknown prompt: {name}")

    options = server.create_initialization_options()
    async with stdio_server() as streams:
        read_stream, write_stream = streams
        try:
            await server.run(read_stream, write_stream, options, raise_exceptions=True)
        except Exception as e:
            logger.error(f"Server error: {str(e)}")
            raise
