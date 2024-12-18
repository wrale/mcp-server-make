import os
import tempfile
from typing import AsyncIterator, Iterator

import pytest
import pytest_asyncio


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
async def server_with_makefile(test_makefile: str) -> AsyncIterator[tuple[str, str]]:
    """Fixture that provides the server with a test Makefile."""
    current_dir = os.getcwd()
    temp_dir = tempfile.mkdtemp()
    os.chdir(temp_dir)

    try:
        yield test_makefile, temp_dir
    finally:
        os.chdir(current_dir)
