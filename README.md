# MCP Server Make

[![CI](https://github.com/wrale/mcp-server-make/actions/workflows/ci.yml/badge.svg)](https://github.com/wrale/mcp-server-make/actions/workflows/ci.yml)
[![Release](https://github.com/wrale/mcp-server-make/actions/workflows/release.yml/badge.svg)](https://github.com/wrale/mcp-server-make/actions/workflows/release.yml)
[![PyPI version](https://badge.fury.io/py/mcp-server-make.svg)](https://badge.fury.io/py/mcp-server-make)

A Model Context Protocol server that provides make functionality. This server enables LLMs to execute make targets from any Makefile in a safe, controlled way.

<a href="https://glama.ai/mcp/servers/g8rwy0077w">
  <img width="380" height="200" src="https://glama.ai/mcp/servers/g8rwy0077w/badge" alt="Server Make MCP server" />
</a>

## Overview

The server exposes make functionality through the Model Context Protocol, allowing LLMs like Claude to:
- Run make targets safely with output capture
- Understand and navigate build processes
- Help with development tasks
- Handle errors appropriately
- Respect working directory context

MCP Server Make works with any valid Makefile - you can use the included opinionated Makefile or your own custom build scripts.

## Quick Start

### Installation

Using `uv` (recommended):
```bash
uv pip install mcp-server-make
```

Using pip:
```bash
pip install mcp-server-make
```

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

## Documentation

For detailed information about using MCP Server Make, please see our documentation:

- [User Guide](docs/user_guide.md) - Complete guide to installation, configuration, and usage
- [Custom Makefiles](docs/custom_makefiles.md) - Creating effective Makefiles for use with MCP Server Make

## Enhancing Development Workflows

This server enables powerful development workflows by giving LLMs direct access to make functionality:

### For Developers

1. **Automated Assistance**
   - Let Claude run and interpret test results 
   - Get build system suggestions and improvements
   - Automate repetitive development tasks

2. **Project Management**
   - Let Claude handle dependency updates
   - Automate release processes
   - Maintain consistent code quality

### Working with Make Targets

MCP Server Make does not automatically discover available targets in your Makefile. To effectively use it with Claude:

1. **Start with `make help`**: Most well-designed Makefiles include a help target

   ```
   Human: Please run make help to see what commands are available.
   ```

2. **Tell Claude about your targets**: Explicitly mention available targets and their purpose

   ```
   Human: Our project has these make targets: test, lint, format, build, and clean.
   ```

3. **Use standard conventions**: Common targets that many Makefiles include:

   - `make test` - Run tests
   - `make lint` - Check code quality 
   - `make format` - Format code
   - `make build` - Build the project
   - `make clean` - Clean build artifacts

The repository includes an opinionated Makefile with additional utility targets - see the [User Guide](docs/user_guide.md) for details on these extended capabilities or for creating your own custom targets.

> **Note**: Claude doesn't remember available targets between conversations. You'll need to introduce them at the start of each conversation.

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

## Available Tools

The server exposes a single tool:

- `make` - Run a make target from the Makefile
    - `target` (string, required): Target name to execute

## Contributing

We welcome contributions to improve mcp-server-make! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for detailed instructions on setting up your development environment, using the project tools, and submitting changes.

## License

MIT License - see LICENSE file for details