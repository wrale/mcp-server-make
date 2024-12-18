
from mcp_server_make.server import serve


async def test_make_command_success(server_with_makefile):
    """Test that make command executes successfully."""
    make_path, working_dir = server_with_makefile
    server = serve(make_path=make_path, working_dir=working_dir)

    # Test list_tools functionality
    tools = await server._list_tools()
    assert len(tools) == 1
    assert tools[0].name == "make"

    # Test successful make command
    result = await server._call_tool("make", {"target": "test-target"})
    assert len(result) == 1
    assert "Test target executed" in result[0].content[0].text


async def test_make_command_failure(server_with_makefile):
    """Test handling of failing make command."""
    make_path, working_dir = server_with_makefile
    server = serve(make_path=make_path, working_dir=working_dir)

    result = await server._call_tool("make", {"target": "failing-target"})
    assert len(result) == 1
    assert "Make failed with error" in result[0].content[0].text


async def test_make_dependency_chain(server_with_makefile):
    """Test execution of make targets with dependencies."""
    make_path, working_dir = server_with_makefile
    server = serve(make_path=make_path, working_dir=working_dir)

    result = await server._call_tool("make", {"target": "dependency-target"})
    output = result[0].content[0].text

    # Verify both targets executed in order
    assert "Base target executed" in output
    assert "Dependency target executed" in output
    # Verify order by checking string positions
    assert output.find("Base target") < output.find("Dependency target")
