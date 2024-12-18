# MCP Server Make

[![CI](https://github.com/wrale/mcp-server-make/actions/workflows/ci.yml/badge.svg)](https://github.com/wrale/mcp-server-make/actions/workflows/ci.yml)
[![Release](https://github.com/wrale/mcp-server-make/actions/workflows/release.yml/badge.svg)](https://github.com/wrale/mcp-server-make/actions/workflows/release.yml)
[![PyPI version](https://badge.fury.io/py/mcp-server-make.svg)](https://badge.fury.io/py/mcp-server-make)

A Model Context Protocol server that provides make functionality. This server enables LLMs to execute make targets from a Makefile in a safe, controlled way.

## Overview

The server exposes make functionality through the Model Context Protocol, allowing LLMs like Claude to:
- Run make targets safely with output capture
- Understand and navigate build processes
- Help with development tasks
- Handle errors appropriately
- Respect working directory context

## Installation

Using `uv` (recommended):
```bash
uv pip install mcp-server-make
```

Using pip:
```bash
pip install mcp-server-make
```

## Configuration

### Basic Usage
```bash
# Run with default Makefile in current directory
uvx mcp-server-make

# Run with specific Makefile and working directory
uvx mcp-server-make --make-path /path/to/Makefile --working-dir /path/to/working/dir
```

### MCP Client Configuration 

To use with Claude Desktop, add to your Claude configuration (`claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "make": {
      "command": "uvx",
      "args": [
        "mcp-server-make",
        "--make-path", "/absolute/path/to/Makefile",
        "--working-dir", "/absolute/path/to/working/dir"
      ]
    }
  }
}
```

## Enhancing Development Workflows

This server enables powerful development workflows by giving LLMs direct access to make functionality:

### For Developers

1. **Automated Assistance**
   - Let Claude run and interpret test results 
   - Get build system suggestions and improvements
   - Automate repetitive development tasks
   - Get immediate feedback on changes

2. **Project Management**
   - Let Claude handle dependency updates
   - Automate release processes
   - Maintain consistent code quality
   - Track project status

### For Claude

1. **Self-Validation Capabilities**
   - Run tests to verify changes: `make test`
   - Check code quality: `make lint`
   - Format code: `make format`
   - Full validation: `make check`

2. **Project Understanding**
   - View project structure: `make x`
   - Check recent changes: `make z`
   - Full context snapshot: `make r`

3. **Independent Development**
   - Manage complete development cycles
   - Self-contained testing and validation
   - Build and prepare releases
   - Generate informed commit messages

## Available Tools

The server exposes a single tool:

- `make` - Run a make target from the Makefile
    - `target` (string, required): Target name to execute

## Error Handling

The server handles common errors gracefully:
- Missing Makefile
- Invalid working directory
- Failed make commands
- Invalid targets

All errors are returned with descriptive messages through the MCP protocol.

## Working Directory Behavior

- If `--working-dir` is specified, changes to that directory before executing make
- If omitted, uses the directory containing the Makefile
- Always restores original working directory after execution

## Example Integration

Here's how Claude can help with development tasks:

```
Human: Can you run our test suite and format any code that needs it?

Claude: I'll help run the tests and format the code:

1. First, let's format the code:
[Calling make tool with args {"target": "format"}]
2 files reformatted, 3 files left unchanged

2. Now let's run the tests:
[Calling make tool with args {"target": "test"}]
Running tests...
4 passed, 0 failed

All formatting and tests completed successfully. The code is now properly formatted and all tests are passing.
```

## Troubleshooting

Common issues:

1. **"Makefile not found"**: Verify the --make-path points to a valid Makefile
2. **"Working directory error"**: Ensure --working-dir exists and is accessible
3. **"Tool execution failed"**: Check make target exists and command succeeds
4. **"Permission denied"**: Verify file and directory permissions

## Contributing

We welcome contributions to improve mcp-server-make! Here's how:

1. Fork the repository
2. Create your feature branch
3. Make your changes
4. Run full validation: `make check`
5. Submit a pull request

## License

MIT License - see LICENSE file for details
