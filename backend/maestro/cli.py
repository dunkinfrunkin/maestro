"""CLI entry point for Maestro."""

from __future__ import annotations

import argparse
import sys

import uvicorn


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Maestro orchestration daemon")
    parser.add_argument("--host", default="127.0.0.1", help="Bind host (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8000, help="Bind port (default: 8000)")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload for development")
    parser.add_argument(
        "--workflow",
        default="WORKFLOW.md",
        help="Path to WORKFLOW.md (default: ./WORKFLOW.md)",
    )
    args = parser.parse_args(argv)

    uvicorn.run(
        "maestro.app:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
    )


if __name__ == "__main__":
    main()
