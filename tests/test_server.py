"""Tests for mcp-server-make."""

import pytest
from mcp.types import Tool
from mcp_server_make.server import Make


def test_tool_schema():
    """Test tool schema is correctly defined."""
    # Verify tool schema
    schema = Make.model_json_schema()
    assert isinstance(schema, dict)
    assert "properties" in schema
    assert "target" in schema["properties"]
    assert schema["properties"]["target"]["type"] == "string"


@pytest.mark.asyncio
async def test_make_tool():
    """Test make tool creation."""
    tool = Tool(
        name="make",
        description="""Run a make target from the Makefile""",
        inputSchema=Make.model_json_schema(),
    )
    assert tool.name == "make"
    assert isinstance(tool.inputSchema, dict)