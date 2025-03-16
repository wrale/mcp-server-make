# Contributing to MCP Server Make

Thank you for your interest in contributing to MCP Server Make! This document provides guidelines and instructions for setting up your development environment and contributing to the project.

## Prerequisites

Before you begin, ensure you have the following installed:
- Python 3.10 or newer (3.12 recommended)
- [uv](https://github.com/astral-sh/uv) - Fast Python package installer and resolver

## Setting Up the Development Environment

### 1. Clone the Repository

```bash
git clone https://github.com/wrale/mcp-server-make.git
cd mcp-server-make
```

### 2. Create and Activate a Virtual Environment

The project uses `uv` for dependency management and virtual environment creation. There are two ways to set up your development environment:

#### Using the Makefile (Recommended)

```bash
# Create virtual environment
make venv

# Set up development environment (installs all dev dependencies)
make dev-setup
```

#### Manual Setup

```bash
# Create a virtual environment
uv venv

# Activate the virtual environment
source .venv/bin/activate  # On Unix/macOS
# Or
.venv\Scripts\activate     # On Windows

# Install the package in development mode with dev dependencies
uv pip install -e ".[dev]"
```

## Development Workflow

The project includes a Makefile with several useful targets to streamline the development process:

### Running Checks

```bash
# Run all checks (format, lint, test)
make check

# Format code
make format

# Lint code
make lint

# Run tests
make test
```

### Building and Installing

```bash
# Build the package
make build

# Install the package locally
make install
```

### Utility Commands

The Makefile includes several utility commands to help with development:

```bash
# Copy project tree structure to clipboard
make x

# Run all checks and copy output to clipboard
make y

# Copy recent git log messages to clipboard
make z

# Run combined commands (git log, tree structure, checks)
make r
```

## Understanding the Tools

### UV

[uv](https://github.com/astral-sh/uv) is a fast Python package installer and resolver used in this project. Key commands:

```bash
# Create a virtual environment
uv venv

# Install a package
uv pip install <package>

# Install in development mode
uv pip install -e .

# Install with extras
uv pip install -e ".[dev]"
```

### Ruff

[Ruff](https://github.com/charliermarsh/ruff) is used for linting and formatting. Configuration is in `pyproject.toml`. Run it using:

```bash
# Check code style
ruff check .

# Format code
ruff format .
```

### MyPy

[MyPy](https://mypy.readthedocs.io/) is used for static type checking. Configuration is in `pyproject.toml`. Run it using:

```bash
mypy src/mcp_server_make
```

### Pytest

[Pytest](https://docs.pytest.org/) is used for testing. Run tests using:

```bash
pytest tests
```

## Contribution Guidelines

1. **Create a branch**: Create a branch for your contribution
2. **Make your changes**: Implement your changes
3. **Run checks**: Ensure all checks pass with `make check`
4. **Write tests**: Add tests for new functionality
5. **Submit a pull request**: Push your changes and create a pull request

## Code Style

- Follow the project's code style enforced by Ruff
- Include docstrings for all functions, classes, and modules
- Write type hints for all functions and methods
- Keep functions small and focused on a single responsibility

## Testing

- Write tests for all new functionality
- Ensure all tests pass before submitting a pull request
- Test edge cases and error conditions

## Pull Request Process

1. Ensure your code passes all checks (`make check`)
2. Update the README.md if necessary
3. Update the documentation for any changed functionality
4. Your pull request will be reviewed by maintainers

## Release Process

Releases are handled through GitHub Actions. When a new release is published:

1. The CI workflow runs tests and builds the package
2. The release workflow builds and publishes the package to PyPI

## Getting Help

If you have any questions or need assistance, please open an issue on GitHub.
