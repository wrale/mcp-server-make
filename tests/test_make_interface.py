"""Test the core Make interface functionality."""

import os
import pathlib
import textwrap
import asyncio
from typing import AsyncGenerator, Generator

import pytest
import pytest_asyncio
from mcp.server import ServerSession
from mcp.server.models import InitializationOptions

from mcp_server_make.exceptions import MakefileError, SecurityError
from mcp_server_make.security import get_validated_path
from mcp_server_make.make import (
    read_makefile,
    validate_makefile_syntax,
    parse_makefile_targets,
)
from mcp_server_make.server import server


class MockStream:
    """Mock IO stream for testing MCP server communication."""

    def __init__(self) -> None:
        """Initialize stream with empty queue and open state."""
        self.queue: asyncio.Queue = asyncio.Queue()
        self.closed: bool = False

    async def send(self, data: any) -> None:
        """Send data through the mock stream."""
        if self.closed:
            raise RuntimeError("Attempted to send on closed stream")
        await self.queue.put(data)

    async def receive(self) -> any:
        """Receive data from the mock stream."""
        if self.closed:
            raise RuntimeError("Attempted to receive from closed stream")
        return await self.queue.get()

    async def aclose(self) -> None:
        """Close the stream and clean up."""
        if not self.closed:
            self.closed = True
            while not self.queue.empty():
                await self.queue.get()


class MockServerSession(ServerSession):
    """Mock server session for testing MCP protocol handlers."""

    def __init__(self) -> None:
        """Initialize mock session."""
        self._read_stream = MockStream()
        self._write_stream = MockStream()
        init_options = InitializationOptions(
            server_name="mock-test",
            server_version="0.1.0",
            capabilities={},
        )
        super().__init__(self._read_stream, self._write_stream, init_options)

    async def send_log_message(self, level: str, data: str) -> None:
        """Mock log message handling."""
        pass


@pytest_asyncio.fixture(scope="function")
async def mock_session() -> AsyncGenerator[ServerSession, None]:
    """Provide a mock server session for testing."""
    session = MockServerSession()
    yield session
    await session._read_stream.aclose()
    await session._write_stream.aclose()


@pytest.fixture
def valid_makefile(tmp_path: pathlib.Path) -> Generator[pathlib.Path, None, None]:
    """Create a valid test Makefile."""
    content = textwrap.dedent("""
        # Test target
        test: ## Run tests
            @echo "Running tests"
            pytest

        # Build target
        build: test ## Build the project
            @echo "Building..."
    """)

    makefile_path = tmp_path / "Makefile"
    makefile_path.write_text(content)

    original_cwd = os.getcwd()
    os.chdir(str(tmp_path))

    yield makefile_path

    os.chdir(original_cwd)


@pytest.fixture
def invalid_makefile(tmp_path: pathlib.Path) -> Generator[pathlib.Path, None, None]:
    """Create an invalid test Makefile."""
    content = textwrap.dedent("""
        .INVALID_DIRECTIVE without colon
        
        test: 
            @echo
    """)

    makefile_path = tmp_path / "Makefile"
    makefile_path.write_text(content)
    yield makefile_path


# Path validation tests
def test_get_validated_path_inside_project(tmp_path: pathlib.Path) -> None:
    """Test path validation accepts paths within project boundaries."""
    test_path = tmp_path / "test.txt"
    os.chdir(str(tmp_path))

    result = get_validated_path(str(test_path))
    assert result.is_absolute()
    assert str(result).startswith(str(tmp_path))


def test_get_validated_path_outside_project(tmp_path: pathlib.Path) -> None:
    """Test path validation rejects paths outside project boundaries."""
    os.chdir(str(tmp_path))

    with pytest.raises(SecurityError, match="outside project boundary"):
        get_validated_path("/etc/passwd")


# Makefile reading and validation tests
@pytest.mark.asyncio
async def test_read_valid_makefile(valid_makefile: pathlib.Path) -> None:
    """Test reading valid Makefile content."""
    content = await read_makefile(valid_makefile)
    assert "test:" in content
    assert "build:" in content


@pytest.mark.asyncio
async def test_read_nonexistent_makefile(tmp_path: pathlib.Path) -> None:
    """Test error handling for missing Makefiles."""
    with pytest.raises(MakefileError, match="Failed to read Makefile"):
        await read_makefile(tmp_path / "NonexistentMakefile")


def test_validate_makefile_syntax_valid(valid_makefile: pathlib.Path) -> None:
    """Test Makefile syntax validation accepts valid content."""
    content = valid_makefile.read_text()
    assert validate_makefile_syntax(content) is True


def test_validate_makefile_syntax_invalid(invalid_makefile: pathlib.Path) -> None:
    """Test Makefile syntax validation rejects invalid content."""
    content = invalid_makefile.read_text()
    with pytest.raises(MakefileError):
        validate_makefile_syntax(content)


# Target parsing tests
@pytest.mark.asyncio
async def test_parse_makefile_targets(valid_makefile: pathlib.Path) -> None:
    """Test extraction of Make targets from valid Makefile."""
    targets = await parse_makefile_targets()

    target_names = {t["name"] for t in targets}
    assert "test" in target_names
    assert "build" in target_names

    test_target = next(t for t in targets if t["name"] == "test")
    assert "Run tests" in test_target["description"]


# MCP Resource Interface tests
@pytest.mark.asyncio
async def test_list_resources_valid_makefile(
    mock_session: ServerSession,
    valid_makefile: pathlib.Path,
) -> None:
    """Test MCP resource listing with valid Makefile."""
    resources = await server.list_resources()

    resource_uris = {r.uri for r in resources}
    assert "make://current/makefile" in resource_uris
    assert "make://targets" in resource_uris


@pytest.mark.asyncio
async def test_read_resource_makefile(
    mock_session: ServerSession,
    valid_makefile: pathlib.Path,
) -> None:
    """Test reading Makefile content through MCP resource interface."""
    content = await server.read_resource("make://current/makefile")
    assert "test:" in content
    assert "build:" in content


@pytest.mark.asyncio
async def test_read_resource_targets(
    mock_session: ServerSession,
    valid_makefile: pathlib.Path,
) -> None:
    """Test reading Make targets through MCP resource interface."""
    content = await server.read_resource("make://targets")
    assert "test" in content
    assert "build" in content


@pytest.mark.asyncio
async def test_read_resource_invalid_uri(
    mock_session: ServerSession,
    valid_makefile: pathlib.Path,
) -> None:
    """Test error handling for invalid resource URIs."""
    with pytest.raises(ValueError, match="Unsupported URI scheme"):
        await server.read_resource("invalid://scheme")
