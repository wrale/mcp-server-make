from .server import serve


def main():
    """MCP Make Server - Make build functionality for MCP"""
    import argparse
    import asyncio

    parser = argparse.ArgumentParser(
        description="give a model the ability to run make commands"
    )
    parser.add_argument("--make-path", type=str, help="Path to makefile")
    parser.add_argument("--working-dir", type=str, help="Working directory")

    args = parser.parse_args()
    asyncio.run(serve(args.make_path, args.working_dir))


if __name__ == "__main__":
    main()
