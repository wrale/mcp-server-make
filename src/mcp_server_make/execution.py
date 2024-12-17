"""Make target execution management with safety controls."""

import asyncio
import os
from pathlib import Path

from .exceptions import MakefileError
from .make import VALID_TARGET_PATTERN
from .security import get_safe_environment, get_validated_path


class ExecutionManager:
    """Manage Make target execution with safety controls."""

    def __init__(self, base_dir: Path, timeout: int = 300):
        """Initialize execution manager.

        Args:
            base_dir: Directory containing the Makefile
            timeout: Maximum execution time in seconds
        """
        self.base_dir = base_dir
        self.timeout = timeout
        self.start_time = 0
        self._original_cwd = None

    async def __aenter__(self):
        self.start_time = asyncio.get_event_loop().time()

        # Store current directory and change to Makefile directory
        self._original_cwd = Path.cwd()
        makefile_dir = get_validated_path(self.base_dir)
        os.chdir(str(makefile_dir))

        return self

    async def run_target(self, target: str) -> str:
        """
        Run a Make target with safety controls.

        Args:
            target: Name of the target to run

        Returns:
            Command output as string
        """
        if not VALID_TARGET_PATTERN.match(target):
            raise ValueError(f"Invalid target name: {target}")

        env = get_safe_environment()

        try:
            proc = await asyncio.create_subprocess_exec(
                "make",
                target,
                env=env,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout, stderr = await asyncio.wait_for(
                proc.communicate(), timeout=self.timeout
            )

            if proc.returncode != 0:
                error_msg = stderr.decode().strip()
                raise MakefileError(f"Target execution failed: {error_msg}")

            return stdout.decode()

        except asyncio.TimeoutError:
            raise MakefileError(f"Target execution exceeded {self.timeout}s timeout")

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        # Restore original working directory
        if self._original_cwd:
            os.chdir(str(self._original_cwd))
