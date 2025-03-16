# MCP Server Make User Guide

This guide explains how to use the MCP Server Make tool effectively, with a focus on using custom Makefiles and getting the most from the integration with LLMs.

## Table of Contents

1. [Introduction](#introduction)
2. [Installation](#installation)
3. [Basic Usage](#basic-usage)
4. [Working with Custom Makefiles](#working-with-custom-makefiles)
5. [Configuration Options](#configuration-options)
6. [Integration with Claude](#integration-with-claude)
7. [Common Workflows](#common-workflows)
8. [Troubleshooting](#troubleshooting)

## Introduction

MCP Server Make is a Model Context Protocol (MCP) server that provides controlled access to `make` functionality. This allows Large Language Models (LLMs) like Claude to execute make targets safely, understand build processes, and assist with development tasks.

The key benefit of MCP Server Make is that it creates a secure bridge between LLMs and the development environment, enabling models to:

- Run build, test, and validation commands
- Generate and validate code changes
- Understand your project's structure and requirements
- Help automate repetitive development tasks

## Installation

### Prerequisites

- Python 3.10 or higher
- A project with a Makefile (built-in or custom)

### Installation Methods

**Using `uv` (recommended):**
```bash
uv pip install mcp-server-make
```

**Using pip:**
```bash
pip install mcp-server-make
```

## Basic Usage

MCP Server Make can be run directly from the command line:

```bash
# Run with default Makefile in current directory
uvx mcp-server-make

# Run with specific Makefile and working directory
uvx mcp-server-make --make-path /path/to/Makefile --working-dir /path/to/working/dir
```

### Command-line Arguments

- `--make-path`: Path to the Makefile you want to use (default: `Makefile` in current directory)
- `--working-dir`: Directory to use as the working directory for make commands (default: directory containing the Makefile)

## Working with Custom Makefiles

MCP Server Make is designed to work with any valid Makefile. While the example Makefile included in the repository provides a comprehensive set of development targets, you can use your own custom Makefiles.

### Using Your Own Makefile

The server is completely agnostic to the actual content of your Makefile - it simply provides a secure interface to execute make targets. This means you can use:

1. Complex build system Makefiles
2. Simple task automation Makefiles
3. Project-specific Makefiles
4. Language-specific Makefiles
5. Any custom Makefile of your design

### Best Practices for Custom Makefiles

When creating a Makefile to use with MCP Server Make and LLMs, consider the following:

1. **Clear Target Names**: Use descriptive, intuitive target names that an LLM can understand
2. **Help Documentation**: Include a `help` target that describes available commands
3. **Informative Output**: Ensure make commands provide clear, structured output
4. **Error Handling**: Include proper error handling and exit codes
5. **Idempotent Commands**: Design targets to be safely executable multiple times
6. **Self-Contained**: Minimize external dependencies where possible

### Example Custom Makefile Structure

Here's a simple template for a custom Makefile that works well with MCP Server Make:

```makefile
.DEFAULT_GOAL := help

# Project settings
PROJECT_NAME = my-project

help: ## Display available commands
	@echo "Available Commands:"
	@echo
	@awk 'BEGIN {FS = ":.*##"} /^[a-zA-Z_-]+:.*?##/ { printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2 }' $(MAKEFILE_LIST)

build: ## Build the project
	# Your build commands here

test: ## Run tests
	# Your test commands here

lint: ## Lint the code
	# Your linting commands here

clean: ## Clean build artifacts
	# Your cleaning commands here

# Define additional targets specific to your project
```

### Working Directory Considerations

The `--working-dir` parameter is crucial when using custom Makefiles, as it determines:

1. The directory from which make commands are executed
2. The default location for relative paths in your Makefile

If not specified, MCP Server Make uses the directory containing the specified Makefile.

## Configuration Options

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

### Environment Variables

MCP Server Make respects standard make environment variables, which you can set in your environment before starting the server:

- `MAKEFLAGS`: Additional flags to pass to make
- `MAKELEVEL`: Current level of make recursion
- `MAKEFILES`: Alternate Makefiles to include

### Security Considerations

MCP Server Make provides a controlled interface to make, but it's important to understand that:

1. It executes make with the permissions of the user running the server
2. It has full access to the specified working directory
3. Targets in the Makefile can execute arbitrary commands

Always review your Makefile for security implications before exposing it through MCP Server Make.

## Integration with Claude

### Introducing Available Targets to Claude

Since Claude doesn't automatically discover the available targets in your Makefile, you should explicitly tell Claude which targets are available. Here are effective approaches:

1. **Start with a help command**: Begin your conversation by asking Claude to run `make help` if your Makefile has a help target. This will list available commands that Claude can then reference.

   ```
   Human: Please run make help to see what commands are available in our project.

   Claude: I'll run the help command to see what's available:

   [Calling make tool with args {"target": "help"}]
   Available Commands:
     build                Build the project
     test                 Run tests
     lint                 Lint code
     format               Format code
     clean                Clean build artifacts
   ```

2. **Explicitly list targets**: Tell Claude which targets are available and what they do.

   ```
   Human: Our Makefile has the following targets:
   - test: Runs the test suite
   - lint: Checks code quality
   - format: Formats code using our style guidelines
   Could you run the lint target?
   ```

3. **Share the Makefile content**: If appropriate, share the content of your Makefile so Claude can understand the available targets.

> **Note**: Each time Claude starts a new conversation, it doesn't remember previously discovered targets. You'll need to reintroduce the available targets at the beginning of each conversation or when switching contexts.

### Working with Claude

Claude can interact with your make targets through the MCP Server Make interface. This enables powerful workflows where Claude can:

### For Development Tasks

1. **Run Tests and Report Results**
   - `make test` to run tests
   - Parse and explain test output
   - Suggest fixes for failing tests

2. **Analyze Code Quality**
   - `make lint` to check code quality
   - Summarize and explain linting errors
   - Help implement fixes

3. **Manage Build Processes**
   - `make build` to build projects
   - Understand and explain build errors
   - Help optimize build configurations

### For Project Management

1. **Track Project Status**
   - Use custom reporting targets like `make status`
   - Get summaries of project health
   - Monitor progress over time

2. **Automate Documentation**
   - Generate docs with targets like `make docs`
   - Update documentation when code changes
   - Create new documentation for undocumented features

### Example Interaction with Claude

```
Human: Can you check if our tests are passing?

Claude: I'll check the test status for you:

[Calling make tool with args {"target": "test"}]
Running tests...
4 passed, 0 failed

Great news! All 4 tests are passing. The test suite completed successfully.

Would you like me to run any other checks on the codebase?
```

## Common Workflows

### Development Assistance

```
# Check code quality
make lint

# Format code
make format

# Run tests
make test

# Full validation
make check
```

### Project Understanding

The included repository Makefile provides some utility targets for project understanding, but these are specific to this repository's Makefile and not universal:

```
# View project structure (specific to this repository's Makefile)
make x

# Check recent changes (specific to this repository's Makefile)
make z

# Full context snapshot (specific to this repository's Makefile)
make r
```

You can create similar targets in your own Makefiles to help Claude understand your project structure.

### Automation

Custom targets can be created for any repetitive task:

```makefile
deploy: ## Deploy the application
    # Deployment commands

update-deps: ## Update dependencies
    # Dependency update commands

generate-report: ## Generate status report
    # Report generation commands
```

## Troubleshooting

### Common Issues

1. **"Makefile not found"**: 
   - Verify the `--make-path` points to a valid Makefile
   - Check file permissions

2. **"Working directory error"**: 
   - Ensure `--working-dir` exists and is accessible
   - Check directory permissions

3. **"Tool execution failed"**: 
   - Check the make target exists in your Makefile
   - Verify the command succeeds when run manually
   - Look for syntax errors in your Makefile

4. **"Permission denied"**: 
   - Check file and directory permissions
   - Ensure the user running the server has appropriate access

### Debugging Tips

1. **Test make commands directly** before using them through MCP Server Make
2. **Review make output** carefully for error messages
3. **Start with simple targets** and gradually introduce complexity
4. **Use verbose flags** in your Makefile for debugging

### Getting Help

If you encounter issues with MCP Server Make, check:
- The GitHub repository issues page
- The project documentation
- Community forums for MCP and Claude integration
