# MCP Make Server

A Model Context Protocol server that provides make functionality. This server enables LLMs to execute make targets from a Makefile in a safe, controlled way.

## Overview

The server exposes make functionality through the Model Context Protocol, allowing LLMs like Claude to:
- Run make targets safely
- Get command output
- Handle errors appropriately
- Respect working directory context

### Installation

Using `uv` (recommended):
```bash
uv pip install mcp-server-make
```

Using pip:
```bash
pip install mcp-server-make
```

### Configuration

#### Basic Usage
```bash
# Run with default Makefile in current directory
mcp-server-make

# Run with specific Makefile and working directory
mcp-server-make --make-path /path/to/Makefile --working-dir /path/to/working/dir
```

#### MCP Client Configuration

To use with Claude Desktop, add to your Claude configuration (`claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "make": {
      "command": "mcp-server-make",
      "args": ["--make-path", "/absolute/path/to/Makefile", "--working-dir", "/absolute/path/to/working/dir"]
    }
  }
}
```

### Available Tools

The server exposes a single tool:

- `make` - Run a make target from the Makefile
    - `target` (string, required): Target name to execute

### Error Handling

The server handles common errors gracefully:
- Missing Makefile
- Invalid working directory
- Failed make commands
- Invalid targets

All errors are returned with descriptive messages through the MCP protocol.

### Working Directory Behavior

- If `--working-dir` is specified, changes to that directory before executing make
- If omitted, uses the directory containing the Makefile
- Always restores original working directory after execution

### Examples

Example usage in Claude:

```
Human: Please run the "test" target in my Makefile.

Claude: I'll use the make tool to run the test target.

[Calling make tool with args {"target": "test"}]
Running tests...
All tests passed!

The test target executed successfully.
```

### Troubleshooting

Common issues:

1. **"Makefile not found"**: Verify the --make-path points to a valid Makefile
2. **"Working directory error"**: Ensure --working-dir exists and is accessible
3. **"Tool execution failed"**: Check make target exists and command succeeds
4. **"Permission denied"**: Verify file and directory permissions

### Contributing

We encourage contributions to help expand and improve mcp-server-make. Whether you want to add new tools, enhance existing functionality, or improve documentation, your input is valuable.

Pull requests are welcome! Feel free to contribute new ideas, bug fixes, or enhancements to make mcp-server-make even more powerful and useful.

### License

mcp-server-make is licensed under the MIT License. This means you are free to use, modify, and distribute the software, subject to the terms and conditions of the MIT License. For more details, please see the LICENSE file in the project repository.