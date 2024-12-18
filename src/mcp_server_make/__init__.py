"""MCP Make Server - Make build functionality for MCP."""

from typing import NoReturn

from .server import serve


def main() -> NoReturn:
    """Run the MCP Make Server.

    This function is the entry point for the MCP Make Server. It parses command line
    arguments and starts the server process.

    Raises:
        SystemExit: Always exits the program after running.
    """
    import argparse
    import asyncio
    import sys

    parser = argparse.ArgumentParser(
        description="give a model the ability to run make commands"
    )
    parser.add_argument("--make-path", type=str, help="Path to makefile")
    parser.add_argument("--working-dir", type=str, help="Working directory")

    args = parser.parse_args()
    try:
        asyncio.run(serve(args.make_path, args.working_dir))
        sys.exit(0)  # Successful execution
    except KeyboardInterrupt:
        sys.exit(0)  # Clean exit on interrupt
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)  # Exit with error
