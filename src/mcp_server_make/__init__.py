"""MCP Server for GNU Make."""

import asyncio

from . import exceptions
from . import make
from . import security
from . import execution
from . import handlers
from .server import main as async_main

__version__ = "0.1.5"
__all__ = ["main", "exceptions", "make", "security", "execution", "handlers"]


def main():
    """CLI entrypoint that runs the async main function."""
    asyncio.run(async_main())
