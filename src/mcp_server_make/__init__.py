"""MCP Server for GNU Make."""

from . import exceptions
from . import make
from . import security
from . import execution
from . import handlers
from .server import main

__version__ = "0.1.0"
__all__ = ["main", "exceptions", "make", "security", "execution", "handlers"]
