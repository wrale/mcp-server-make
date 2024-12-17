"""Test the core Make interface functionality."""

import os
import pathlib
import textwrap
import asyncio
from typing import AsyncGenerator, Generator, Dict, Any

import pytest
import pytest_asyncio
from mcp.server import RequestContext, ServerSession
from mcp.server.models import InitializationOptions

from mcp_server_make.exceptions import MakefileError, SecurityError
from mcp_server_make.security import get_validated_path
from mcp_server_make.make import (
    read_makefile,
    validate_makefile_syntax,
    parse_makefile_targets,
)
from mcp_server_make.server import server, request_context


# Testing infrastructure
class EmptyContext:
    """Empty context for testing."""

    def __init__(self) -> None:
        """Initialize an empty context."""
        self.data: Dict[str, Any] = {}


class MockStream:
    """Mock stream for testing."""

    def __init__(self) -> None:
        """Initialize the stream."""
        self.queue: asyncio.Queue = asyncio.Queue()
        self.closed = False

    async def send(self, data: Any) -> None:
        """Send data to the stream."""
        if self.closed:
            raise RuntimeError("Stream closed")
        await self.queue.put(data)

    async def receive(self) -> Any:
        """Receive data from the stream."""
        if self.closed:
            raise RuntimeError("Stream closed")
        return await self.queue.get()

    async def aclose(self) -> None:
        """Close the stream."""
        self.closed = True
        # Clear any remaining items
        while not self.queue.empty():
            await self.queue.get()


class MockServerSession(ServerSession):
    """Mock MCP server session for testing."""

    def __init__(self) -> None:
        """Initialize the mock session."""
        read_stream = MockStream()
        write_stream = MockStream()
        init_options = InitializationOptions(
            server_name="mock-test",
            server_version="0.1.0",
            capabilities={},
        )
        super().__init__(read_stream, write_stream, init_options)

    async def send_log_message(self, level: str, data: str) -> None:
        """Mock log message sending."""
        pass  # No-op for testing


@pytest_asyncio.fixture(scope="function")
async def mock_session() -> AsyncGenerator[ServerSession, None]:
    """Create a mock server session."""
    session = MockServerSession()
    yield session
    # Ensure cleanup of any resources
    await session._read_stream.aclose()  # type: ignore
    await session._write_stream.aclose()  # type: ignore


@pytest_asyncio.fixture(scope="function")
async def request_ctx(
    mock_session: ServerSession,
) -> AsyncGenerator[RequestContext[ServerSession], None]:
    """Setup request context for tests."""
    ctx = RequestContext(session=mock_session, context=EmptyContext())

    # Set context and handle cleanup
    token = request_context.set(ctx)
    try:
        yield ctx
    finally:
        request_context.reset(token)


# Fixtures for test Makefiles
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

    # Allow the Makefile to be found in the current directory
    original_cwd = os.getcwd()
    os.chdir(str(tmp_path))

    yield makefile_path

    # Restore original working directory
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


# Test Path Validation
def test_get_validated_path_inside_project(tmp_path: pathlib.Path) -> None:
    """Test path validation within project boundaries."""
    test_path = tmp_path / "test.txt"
    os.chdir(str(tmp_path))  # Set current directory for test

    result = get_validated_path(str(test_path))
    assert result.is_absolute()
    assert str(result).startswith(str(tmp_path))


def test_get_validated_path_outside_project(tmp_path: pathlib.Path) -> None:
    """Test path validation catches paths outside project."""
    os.chdir(str(tmp_path))  # Set current directory for test

    with pytest.raises(SecurityError, match="outside project boundary"):
        get_validated_path("/etc/passwd")


# Test Makefile Reading and Validation
@pytest.mark.asyncio
async def test_read_valid_makefile(valid_makefile: pathlib.Path) -> None:
    """Test reading a valid Makefile."""
    content = await read_makefile(valid_makefile)
    assert "test:" in content
    assert "build:" in content


@pytest.mark.asyncio
async def test_read_nonexistent_makefile(tmp_path: pathlib.Path) -> None:
    """Test reading a nonexistent Makefile fails properly."""
    with pytest.raises(MakefileError, match="Failed to read Makefile"):
        await read_makefile(tmp_path / "NonexistentMakefile")


def test_validate_makefile_syntax_valid(valid_makefile: pathlib.Path) -> None:
    """Test Makefile syntax validation with valid content."""
    content = valid_makefile.read_text()
    assert validate_makefile_syntax(content) is True


def test_validate_makefile_syntax_invalid(invalid_makefile: pathlib.Path) -> None:
    """Test Makefile syntax validation with invalid content."""
    content = invalid_makefile.read_text()
    with pytest.raises(MakefileError):
        validate_makefile_syntax(content)


# Test Target Parsing
@pytest.mark.asyncio
async def test_parse_makefile_targets(valid_makefile: pathlib.Path) -> None:
    """Test parsing Makefile targets."""
    targets = await parse_makefile_targets()

    # Verify we found both targets
    target_names = {t["name"] for t in targets}
    assert "test" in target_names
    assert "build" in target_names

    # Verify descriptions are parsed
    test_target = next(t for t in targets if t["name"] == "test")
    assert "Run tests" in test_target["description"]


# Test MCP Resource Interface
@pytest.mark.asyncio
async def test_list_resources_valid_makefile(
    request_ctx: RequestContext[ServerSession],
    valid_makefile: pathlib.Path,
) -> None:
    """Test listing available Make resources."""
    resources = await server.list_resources()

    # Should find both the Makefile and targets resources
    resource_uris = {r.uri for r in resources}
    assert "make://current/makefile" in resource_uris
    assert "make://targets" in resource_uris


@pytest.mark.asyncio
async def test_read_resource_makefile(
    request_ctx: RequestContext[ServerSession],
    valid_makefile: pathlib.Path,
) -> None:
    """Test reading Makefile resource."""
    content = await server.read_resource("make://current/makefile")
    assert "test:" in content
    assert "build:" in content


@pytest.mark.asyncio
async def test_read_resource_targets(
    request_ctx: RequestContext[ServerSession],
    valid_makefile: pathlib.Path,
) -> None:
    """Test reading targets resource."""
    content = await server.read_resource("make://targets")
    assert "test" in content
    assert "build" in content


@pytest.mark.asyncio
async def test_read_resource_invalid_uri(
    request_ctx: RequestContext[ServerSession],
    valid_makefile: pathlib.Path,
) -> None:
    """Test reading with invalid URI scheme."""
    with pytest.raises(ValueError, match="Unsupported URI scheme"):
        await server.read_resource("invalid://scheme")
