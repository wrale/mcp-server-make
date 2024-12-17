"""Core Make functionality for the MCP Make Server."""

import asyncio
import re
from pathlib import Path
from typing import List

from .exceptions import MakefileError
from .security import get_validated_path

# Regular expression for validating Make target names
VALID_TARGET_PATTERN = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_-]*$")


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


async def parse_makefile_targets(makefile_dir: Path) -> List[dict]:
    """
    Parse Makefile to extract targets and their metadata.

    Args:
        makefile_dir: Directory containing the Makefile to parse

    Returns:
        List of target dictionaries with metadata
    """
    path = get_validated_path(makefile_dir, "Makefile")
    content = await read_makefile(path)

    targets = []
    current_comment = []
    current_description = None

    for line in content.splitlines():
        line = line.strip()

        if line.startswith("#"):
            current_comment.append(line[1:].strip())
        elif ":" in line and not line.startswith("\t"):
            target = line.split(":", 1)[0].strip()

            # Extract description from ## comment if present
            description_parts = line.split("##", 1)
            if len(description_parts) > 1:
                current_description = description_parts[1].strip()

            if VALID_TARGET_PATTERN.match(target):
                description = current_description or " ".join(current_comment) or None
                targets.append({"name": target, "description": description})
            current_comment = []
            current_description = None
        else:
            current_comment = []

    return targets
