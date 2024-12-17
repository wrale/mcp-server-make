"""Security controls for the MCP Make Server."""

from pathlib import Path
from typing import Optional

from .exceptions import SecurityError


def get_validated_path(base_dir: Path, subpath: Optional[str] = None) -> Path:
    """
    Validate and resolve a path within project boundaries.

    Args:
        base_dir: Base directory containing Makefile (project root)
        subpath: Optional path relative to base_dir

    Returns:
        Resolved Path object

    Raises:
        SecurityError: If path validation fails
    """
    try:
        # Resolve the base directory
        base = base_dir.resolve()

        # If no subpath, return base
        if subpath is None:
            return base

        # Resolve requested path relative to base
        requested = (base / subpath).resolve()

        # Ensure path is within base directory tree
        if not str(requested).startswith(str(base)):
            raise SecurityError("Path access denied: outside project boundary")

        return requested
    except Exception as e:
        raise SecurityError(f"Invalid path: {str(e)}")


def get_safe_environment() -> dict:
    """Get a sanitized environment for Make execution."""
    import os

    env = os.environ.copy()
    # Remove potentially dangerous variables
    for key in list(env.keys()):
        if key.startswith(("LD_", "DYLD_", "PATH")):
            del env[key]
    return env
