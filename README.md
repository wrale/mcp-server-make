# mcp-server-make

MCP Server for GNU Make - providing controlled and secure access to Make systems from LLMs.

## Features

### Resources
- `make://current/makefile` - Access current Makefile content securely
- `make://targets` - List available Make targets with documentation

### Tools
- `list-targets`: List available Make targets
  - Returns target names and documentation
  - Optional pattern filtering for searching targets
- `run-target`: Execute Make targets safely
  - Required: target name
  - Optional: timeout (1-3600 seconds, default 300)

## Quick Start

### Prerequisites
- Python 3.12+
- GNU Make
- pip or uv package manager

### Installation

Using uv (recommended):
```bash
uvx mcp-server-make
```

Using pip:
```bash
pip install mcp-server-make
```

### Claude Desktop Integration

Add to your Claude Desktop configuration:

MacOS:
```bash
nano ~/Library/Application\ Support/Claude/claude_desktop_config.json
```

Windows:
```bash
notepad %APPDATA%\Claude\claude_desktop_config.json
```

Add configuration:
```json
{
  "mcpServers": {
    "mcp-server-make": {
      "command": "uv",
      "args": [
        "--directory", 
        "/path/to/server",
        "run",
        "mcp-server-make", 
        "--makefile-dir", "/path/to/project"
      ]
    }
  }
}
```

- `--directory`: Path to the installed mcp-server-make package
- `--makefile-dir`: Directory containing the Makefile to manage

Restart Claude Desktop to activate the Make server.

## Usage Examples

### List Available Targets
```
I see you have a Makefile. Can you list the available targets?
```

### View Target Documentation
```
What does the 'build' target do?
```

### Run Tests
```
Please run the test target with a 2 minute timeout.
```

### View Makefile
```
Show me the current Makefile content.
```

## Development

### Local Development Setup
```bash
# Clone repository
git clone https://github.com/modelcontextprotocol/mcp-server-make
cd mcp-server-make

# Create virtual environment
uv venv
source .venv/bin/activate  # Unix/MacOS
.venv\Scripts\activate     # Windows

# Install dependencies
make dev-setup

# Run tests and checks
make check
```

### Testing with MCP Inspector

Test the server using the MCP Inspector:
```bash
npx @modelcontextprotocol/inspector uv --directory /path/to/mcp-server-make run mcp-server-make --makefile-dir /path/to/project
```

## Security Features

Version 0.1.0 implements several security controls:

- Path validation and directory boundary enforcement
- Target name sanitization and command validation
- Resource and timeout limits for command execution
- Restricted environment access and cleanup
- Error isolation and safe propagation

## Behavior Details

### Resource Access
- Makefile content is read-only and validated
- Target listing includes names and documentation
- Full path validation prevents traversal attacks
- Resources require proper make:// URIs

### Tool Execution
- Targets are sanitized and validated
- Execution occurs in controlled environment
- Timeouts prevent infinite execution
- Clear error messages for failures
- Resource cleanup after execution

### Error Handling
- Type-safe error propagation
- Context-aware error messages
- Clean error isolation
- No error leakage

## Known Limitations

Version 0.1.0 has the following scope limitations:

- Read-only Makefile access
- Single Makefile per working directory
- No support for include directives
- Basic target pattern matching only
- No variable expansion in documentation

## Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new features
4. Ensure all checks pass (`make check`)
5. Submit a pull request

## License

MIT - See LICENSE file for details.

## Support

- GitHub Issues: Bug reports and feature requests
- GitHub Discussions: Questions and community help

## Version History

### 0.1.0
- Initial stable release
- Basic Makefile access and target execution
- Core security controls
- Claude Desktop integration
- Configurable Makefile directory