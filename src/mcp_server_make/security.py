"""Security controls for the MCP Make Server."""

from pathlib import Path
from typing import Optional

from .exceptions import SecurityError


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


def get_safe_environment() -> dict:
    """Get a sanitized environment for Make execution."""
    import os

    env = os.environ.copy()
    # Remove potentially dangerous variables
    for key in list(env.keys()):
        if key.startswith(("LD_", "DYLD_", "PATH")):
            del env[key]
    return env
