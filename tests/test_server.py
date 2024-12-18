"""Tests for the MCP make server."""

import pytest
from mcp.types import ListToolsResultSchema, CallToolResultSchema
from mcp.shared.exceptions import McpError


@pytest.mark.asyncio
async def test_list_tools(mcp_client):
    """Test listing available tools via MCP protocol."""
    client, _, _ = mcp_client

    result = await client.request({"method": "tools/list"}, ListToolsResultSchema)

    assert len(result.tools) == 1
    tool = result.tools[0]
    assert tool.name == "make"
    assert "Run a make target" in tool.description
    assert tool.inputSchema["type"] == "object"
    assert "target" in tool.inputSchema["properties"]


@pytest.mark.asyncio
async def test_successful_make_target(mcp_client):
    """Test successful execution of a make target."""
    client, _, _ = mcp_client

    result = await client.request(
        {
            "method": "tools/call",
            "params": {"name": "make", "arguments": {"target": "test-target"}},
        },
        CallToolResultSchema,
    )

    assert len(result.content) == 1
    assert result.content[0].type == "text"
    assert "Test target executed" in result.content[0].text


@pytest.mark.asyncio
async def test_failing_make_target(mcp_client):
    """Test handling of a failing make target."""
    client, _, _ = mcp_client

    result = await client.request(
        {
            "method": "tools/call",
            "params": {"name": "make", "arguments": {"target": "failing-target"}},
        },
        CallToolResultSchema,
    )

    assert len(result.content) == 1
    assert result.content[0].type == "text"
    assert "Make failed with error" in result.content[0].text


@pytest.mark.asyncio
async def test_make_target_dependencies(mcp_client):
    """Test execution of make targets with dependencies."""
    client, _, _ = mcp_client

    result = await client.request(
        {
            "method": "tools/call",
            "params": {"name": "make", "arguments": {"target": "dependency-target"}},
        },
        CallToolResultSchema,
    )

    assert len(result.content) == 1
    output = result.content[0].text

    # Verify both targets executed in order
    assert "Base target executed" in output
    assert "Dependency target executed" in output
    # Verify order by checking string positions
    assert output.find("Base target") < output.find("Dependency target")


@pytest.mark.asyncio
async def test_invalid_tool_name(mcp_client):
    """Test error handling for invalid tool name."""
    client, _, _ = mcp_client

    with pytest.raises(McpError) as exc_info:
        await client.request(
            {
                "method": "tools/call",
                "params": {
                    "name": "invalid-tool",
                    "arguments": {"target": "test-target"},
                },
            },
            CallToolResultSchema,
        )

    assert "Unknown tool" in str(exc_info.value)
