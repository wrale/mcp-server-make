"""Make target execution management with safety controls."""

import asyncio

from .exceptions import MakefileError
from .make import VALID_TARGET_PATTERN
from .security import get_safe_environment


class ExecutionManager:
    """Manage Make target execution with safety controls."""

    def __init__(self, timeout: int = 300):
        self.timeout = timeout
        self.start_time = 0

    async def __aenter__(self):
        self.start_time = asyncio.get_event_loop().time()
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
        pass
