"""Test the core Make interface functionality.

This module provides tests for the MCP Make Server's core functionality, including
request context management, file system operations, and resource handling. It uses
pytest-asyncio for managing async test execution and provides mock implementations
of MCP server components.
"""

import os
import uuid
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


def generate_request_meta() -> Dict[str, Any]:
    """Generate test request metadata.

    Returns consistent metadata dictionary for test requests while simulating
    actual MCP request properties. This keeps tests deterministic while
    matching protocol requirements.

    Returns:
        Dictionary containing required request metadata fields
    """
    return {
        "client_name": "test-client",
        "client_version": "0.1.0",
        "protocol_version": "1.0",
        "capabilities": {},  # Empty capabilities for testing
    }


# Testing infrastructure classes
class EmptyContext:
    """Minimal context for testing MCP request handling.

    This provides the minimal implementation needed for request context testing
    while keeping test setup simple and maintainable.
    """

    def __init__(self) -> None:
        """Initialize an empty test context."""
        self.data: Dict[str, Any] = {}


class MockStream:
    """Mock IO stream for testing MCP server communication.

    Provides a simple queue-based implementation that satisfies the MCP protocol's
    stream requirements while being easily testable. The stream maintains an
    internal state and properly handles closures.
    """

    def __init__(self) -> None:
        """Initialize stream with empty queue and open state."""
        self.queue: asyncio.Queue = asyncio.Queue()
        self.closed: bool = False

    async def send(self, data: Any) -> None:
        """Send data through the mock stream.

        Args:
            data: Data to send through the stream

        Raises:
            RuntimeError: If the stream is closed
        """
        if self.closed:
            raise RuntimeError("Attempted to send on closed stream")
        await self.queue.put(data)

    async def receive(self) -> Any:
        """Receive data from the mock stream.

        Returns:
            Next item from the stream queue

        Raises:
            RuntimeError: If the stream is closed
        """
        if self.closed:
            raise RuntimeError("Attempted to receive from closed stream")
        return await self.queue.get()

    async def aclose(self) -> None:
        """Close the stream and clean up any pending data."""
        if not self.closed:
            self.closed = True
            # Drain any remaining items to prevent resource leaks
            while not self.queue.empty():
                await self.queue.get()


class MockServerSession(ServerSession):
    """Mock server session for testing MCP protocol handlers.

    Provides a minimal implementation that satisfies the MCP server requirements
    while being suitable for testing. Uses mock streams for IO and provides
    no-op implementations of optional features.
    """

    def __init__(self) -> None:
        """Initialize mock session with test streams and options."""
        # Create mock IO streams for testing
        self._read_stream = MockStream()
        self._write_stream = MockStream()

        # Create minimal initialization options
        init_options = InitializationOptions(
            server_name="mock-test",
            server_version="0.1.0",
            capabilities={},  # Empty capabilities for testing
        )

        # Initialize base session
        super().__init__(self._read_stream, self._write_stream, init_options)

    async def send_log_message(self, level: str, data: str) -> None:
        """Mock log message handling.

        The mock implementation deliberately ignores log messages as they are not
        relevant for testing resource functionality.
        """
        pass  # No-op for testing


# Test fixtures
@pytest_asyncio.fixture(scope="function")
async def mock_session() -> AsyncGenerator[ServerSession, None]:
    """Provide a mock server session for testing.

    The fixture manages the lifecycle of the mock session including cleanup of
    IO streams. Using function scope ensures test isolation.

    Yields:
        Configured MockServerSession instance
    """
    session = MockServerSession()
    yield session
    # Clean up mock streams
    await session._read_stream.aclose()
    await session._write_stream.aclose()


@pytest_asyncio.fixture(scope="function")
async def request_ctx(
    mock_session: ServerSession,
) -> AsyncGenerator[RequestContext[ServerSession], None]:
    """Set up MCP request context for testing.

    Manages request context lifecycle including proper cleanup. Uses the mock
    session fixture to provide a complete test environment.

    Args:
        mock_session: Mock server session (injected by pytest)

    Yields:
        Configured RequestContext instance
    """
    # Create RequestContext with required parameters
    ctx = RequestContext(
        session=mock_session,
        request_id=str(uuid.uuid4()),  # Generate unique request ID
        meta=generate_request_meta(),  # Add metadata as direct dictionary
    )

    # Set context and ensure cleanup
    token = request_context.set(ctx)
    try:
        yield ctx
    finally:
        request_context.reset(token)


@pytest.fixture
def valid_makefile(tmp_path: pathlib.Path) -> Generator[pathlib.Path, None, None]:
    """Create a valid test Makefile.

    Sets up a temporary Makefile with known content for testing Make operations.
    Handles directory changes to allow proper path resolution.

    Args:
        tmp_path: Temporary directory (provided by pytest)

    Yields:
        Path to the test Makefile
    """
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

    # Save original directory and change to test directory
    original_cwd = os.getcwd()
    os.chdir(str(tmp_path))

    yield makefile_path

    # Restore original directory
    os.chdir(original_cwd)


@pytest.fixture
def invalid_makefile(tmp_path: pathlib.Path) -> Generator[pathlib.Path, None, None]:
    """Create an invalid test Makefile.

    Sets up a Makefile with known invalid content for testing error handling.

    Args:
        tmp_path: Temporary directory (provided by pytest)

    Yields:
        Path to the invalid test Makefile
    """
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

    # Verify target detection
    target_names = {t["name"] for t in targets}
    assert "test" in target_names
    assert "build" in target_names

    # Verify description parsing
    test_target = next(t for t in targets if t["name"] == "test")
    assert "Run tests" in test_target["description"]


# MCP Resource Interface tests
@pytest.mark.asyncio
async def test_list_resources_valid_makefile(
    request_ctx: RequestContext[ServerSession],
    valid_makefile: pathlib.Path,
) -> None:
    """Test MCP resource listing with valid Makefile.

    Verifies that both the Makefile and targets resources are properly exposed
    through the MCP interface.
    """
    resources = await server.list_resources()

    # Verify expected resources
    resource_uris = {r.uri for r in resources}
    assert "make://current/makefile" in resource_uris
    assert "make://targets" in resource_uris


@pytest.mark.asyncio
async def test_read_resource_makefile(
    request_ctx: RequestContext[ServerSession],
    valid_makefile: pathlib.Path,
) -> None:
    """Test reading Makefile content through MCP resource interface."""
    content = await server.read_resource("make://current/makefile")
    assert "test:" in content
    assert "build:" in content


@pytest.mark.asyncio
async def test_read_resource_targets(
    request_ctx: RequestContext[ServerSession],
    valid_makefile: pathlib.Path,
) -> None:
    """Test reading Make targets through MCP resource interface."""
    content = await server.read_resource("make://targets")
    assert "test" in content
    assert "build" in content


@pytest.mark.asyncio
async def test_read_resource_invalid_uri(
    request_ctx: RequestContext[ServerSession],
    valid_makefile: pathlib.Path,
) -> None:
    """Test error handling for invalid resource URIs."""
    with pytest.raises(ValueError, match="Unsupported URI scheme"):
        await server.read_resource("invalid://scheme")
