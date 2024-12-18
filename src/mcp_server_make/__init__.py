"""MCP Server for GNU Make."""

import asyncio
from . import exceptions
from .server import main as async_main

__version__ = "0.1.8"
__all__ = ["main", "exceptions"]


def main():
    """CLI entrypoint that runs the async main function."""
    asyncio.run(async_main())
