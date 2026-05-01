"""Configuration for the Enoch MCP server."""

from __future__ import annotations

import argparse
import os
from collections.abc import Sequence
from dataclasses import dataclass

DEFAULT_API_URL = "http://localhost:8787"


@dataclass(frozen=True, slots=True)
class EnochMCPConfig:
    """Runtime configuration for calls to Enoch's HTTP API."""

    api_url: str = DEFAULT_API_URL
    api_token: str | None = None

    @property
    def normalized_api_url(self) -> str:
        return self.api_url.rstrip("/")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="enoch-mcp",
        description="Run an MCP stdio server for the Enoch FastAPI control plane.",
    )
    parser.add_argument(
        "--api-url",
        default=os.environ.get("ENOCH_API_URL", DEFAULT_API_URL),
        help=f"Base URL for Enoch's API (default: {DEFAULT_API_URL} or ENOCH_API_URL).",
    )
    parser.add_argument(
        "--api-token",
        default=os.environ.get("ENOCH_API_TOKEN"),
        help="Bearer token for Enoch's API (default: ENOCH_API_TOKEN).",
    )
    return parser


def load_config(argv: Sequence[str] | None = None) -> EnochMCPConfig:
    args = build_parser().parse_args(argv)
    return EnochMCPConfig(api_url=args.api_url, api_token=args.api_token)
