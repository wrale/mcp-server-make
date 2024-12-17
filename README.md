# mcp-server-make

MCP Server for GNU Make - providing controlled and secure access to Make systems from LLMs.

## Components

### Resources

The server implements foundational GNU Make access through:
- `make://current/makefile` - Access the current Makefile content
- `make://targets` - List available Make targets with metadata
- Basic path validation and security controls

### Tools

The server provides core Make interaction tools:
- `list-targets`: Enumerate available targets with documentation
  - Returns target names, dependencies, and descriptions
  - Optional pattern filtering
- `run-target`: Execute Make targets safely
  - Required target name parameter
  - Optional timeout configuration
  - Built-in security controls and validation

## Configuration

The server requires Python 3.12 or higher and a GNU Make installation.

### Environment Setup

1. Install dependencies:
```bash
uv venv
source .venv/bin/activate  # On Unix/Mac
.venv\Scripts\activate     # On Windows
uv pip install -e .
```

2. Development setup:
```bash
make dev-setup
```

### Claude Desktop Integration

Add to Claude Desktop configuration:
- MacOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
- Windows: `%APPDATA%/Claude/claude_desktop_config.json`

<details>
  <summary>Development Configuration</summary>

```json
{
  "mcpServers": {
    "mcp-server-make": {
      "command": "uv",
      "args": [
        "--directory",
        "/path/to/mcp-server-make",
        "run",
        "mcp-server-make"
      ]
    }
  }
}
```
</details>

<details>
  <summary>Production Configuration (after PyPI publish)</summary>

```json
{
  "mcpServers": {
    "mcp-server-make": {
      "command": "uvx",
      "args": ["mcp-server-make"]
    }
  }
}
```
</details>

## Development

### Local Development

1. Create a development environment:
```bash
make dev-setup
```

2. Run tests and formatting:
```bash
make check
```

3. Start the development server:
```bash
make dev
```

### Debugging

For debugging, we recommend using the MCP Inspector:

```bash
npx @modelcontextprotocol/inspector uv --directory /path/to/mcp-server-make run mcp-server-make
```

The Inspector provides an interactive web interface for testing resources and tools.

### Security Notes

The server implements several security controls:
- Path validation and boundary enforcement
- Target name and command sanitization
- Execution timeouts and resource limits
- Restricted environment access

### Building for Distribution

1. Build package:
```bash
make build
```

2. Publish to PyPI (maintainers only):
```bash
make publish
```

Requires PyPI credentials set via:
- Token: `UV_PUBLISH_TOKEN`
- Or username/password: `UV_PUBLISH_USERNAME` and `UV_PUBLISH_PASSWORD`
