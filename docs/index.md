# MCP Server Make Documentation

Welcome to the MCP Server Make documentation. This tool enables LLMs to execute make targets from any Makefile in a safe, controlled way, creating powerful development workflows.

## Documentation Index

- [User Guide](user_guide.md) - Complete guide to installation, configuration, and usage
- [Custom Makefiles](custom_makefiles.md) - Creating effective Makefiles for use with MCP Server Make

## What is MCP Server Make?

MCP Server Make is a Model Context Protocol (MCP) server that provides controlled access to `make` functionality. This allows Large Language Models (LLMs) like Claude to execute make targets safely, understand build processes, and assist with development tasks.

The key benefit is that it creates a secure bridge between LLMs and the development environment, enabling models to:

- Run build, test, and validation commands
- Generate and validate code changes
- Understand your project's structure and requirements
- Help automate repetitive development tasks

## Key Features

- **Works with Any Makefile**: Use the included opinionated Makefile or any custom Makefile
- **Safe Execution**: Controlled access to make functionality
- **Flexible Configuration**: Specify custom Makefiles and working directories
- **Error Handling**: Graceful handling of common errors
- **Clear Output**: Structured output for LLM understanding

## Getting Started

See the [User Guide](user_guide.md) for complete installation and usage instructions.

Quick installation:

```bash
# Using uv (recommended)
uv pip install mcp-server-make

# Using pip
pip install mcp-server-make
```

Basic usage:

```bash
# With default Makefile in current directory
uvx mcp-server-make

# With custom Makefile and working directory
uvx mcp-server-make --make-path /path/to/Makefile --working-dir /path/to/working/dir
```

## Resources

- [GitHub Repository](https://github.com/wrale/mcp-server-make)
- [PyPI Package](https://pypi.org/project/mcp-server-make/)
- [Contributing Guide](../CONTRIBUTING.md)
