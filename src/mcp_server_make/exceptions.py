"""Custom exceptions for the MCP Make Server."""


class MakefileError(Exception):
    """Raised when there are issues with Makefile operations."""

    pass


class SecurityError(Exception):
    """Raised for security-related violations."""

    pass
