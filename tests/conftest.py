import os
import tempfile
from typing import AsyncIterator, Iterator

import pytest
import pytest_asyncio
from mcp.client.client import Client
from mcp.client.stdio import StdioClientTransport


@pytest.fixture
def test_makefile() -> Iterator[str]:
    """Fixture that creates a temporary Makefile for testing."""
    with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
        f.write("""
.PHONY: test-target
test-target:
	@echo "Test target executed"

.PHONY: failing-target
failing-target:
	@exit 1

# Simple dependency test
.PHONY: dependency-target base-target
base-target:
	@echo "Base target executed"

dependency-target: base-target
	@echo "Dependency target executed"
""")
        f.flush()
        yield f.name
    os.unlink(f.name)


@pytest_asyncio.fixture
async def mcp_client(test_makefile: str) -> AsyncIterator[tuple[Client, str, str]]:
    """Fixture that provides a connected MCP client with test Makefile."""
    current_dir = os.getcwd()
    temp_dir = tempfile.mkdtemp()

    client = Client(
        {
            "name": "test-client",
            "version": "0.1.0",
        },
        {
            "capabilities": {},
        },
    )

    transport = StdioClientTransport(
        {
            "command": "python",
            "args": [
                "-m",
                "mcp_server_make",
                "--make-path",
                test_makefile,
                "--working-dir",
                temp_dir,
            ],
        }
    )

    await client.connect(transport)

    try:
        yield client, test_makefile, temp_dir
    finally:
        await transport.close()
        os.chdir(current_dir)
