"""Command line entry point for enoch-mcp."""

from __future__ import annotations

from .config import load_config
from .server import run


def main() -> None:
    run(load_config())


if __name__ == "__main__":
    main()
