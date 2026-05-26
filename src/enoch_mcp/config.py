"""Configuration for the Enoch MCP server."""

from __future__ import annotations

import argparse
import json
import os
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

DEFAULT_API_URL = "http://localhost:8787"


@dataclass(frozen=True, slots=True)
class WorkerProbeTarget:
    """Optional direct diagnostic target for one Enoch worker lane."""

    lane: str
    api_url: str | None = None
    api_token: str | None = None
    ssh_host: str | None = None
    ssh_user: str | None = None
    ssh_port: int | None = None
    service_name: str = "enoch-control-plane"
    project_root: str | None = None
    state_dir: str | None = None
    log_paths: tuple[str, ...] = ()
    ssh_timeout_seconds: int = 12
    api_timeout_seconds: int = 10


@dataclass(frozen=True, slots=True)
class EnochMCPConfig:
    """Runtime configuration for calls to Enoch's HTTP API."""

    api_url: str = DEFAULT_API_URL
    api_token: str | None = None
    worker_probe_targets: dict[str, WorkerProbeTarget] | None = None

    @property
    def normalized_api_url(self) -> str:
        return self.api_url.rstrip("/")

    @property
    def resolved_worker_probe_targets(self) -> dict[str, WorkerProbeTarget]:
        return self.worker_probe_targets or {}


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
    parser.add_argument(
        "--worker-probes-json",
        default=os.environ.get("ENOCH_WORKER_PROBES_JSON"),
        help=(
            "Optional JSON worker probe map. Keys are lane names; values may include "
            "api_url, api_token, ssh_host, ssh_user, ssh_port, service_name, "
            "project_root, state_dir, and log_paths."
        ),
    )
    parser.add_argument(
        "--worker-probes-file",
        default=os.environ.get("ENOCH_WORKER_PROBES_FILE"),
        help="Optional path to a JSON worker probe map.",
    )
    return parser


def load_config(argv: Sequence[str] | None = None) -> EnochMCPConfig:
    args = build_parser().parse_args(argv)
    return EnochMCPConfig(
        api_url=args.api_url,
        api_token=args.api_token,
        worker_probe_targets=load_worker_probe_targets(
            json_text=args.worker_probes_json,
            file_path=args.worker_probes_file,
        ),
    )


def load_worker_probe_targets(
    *, json_text: str | None = None, file_path: str | None = None
) -> dict[str, WorkerProbeTarget]:
    """Load optional worker probe targets from JSON config."""
    data: dict[str, Any] = {}
    if file_path:
        raw = Path(file_path).expanduser().read_text(encoding="utf-8")
        file_data = json.loads(raw)
        if not isinstance(file_data, dict):
            raise ValueError("worker probe file must contain a JSON object")
        data.update(file_data)
    if json_text:
        json_data = json.loads(json_text)
        if not isinstance(json_data, dict):
            raise ValueError("worker probe JSON must contain an object")
        data.update(json_data)
    return _worker_targets_from_mapping(data)


def _worker_targets_from_mapping(data: dict[str, Any]) -> dict[str, WorkerProbeTarget]:
    targets: dict[str, WorkerProbeTarget] = {}
    for lane, raw_target in data.items():
        if not isinstance(raw_target, dict):
            raise ValueError(f"worker probe target for {lane!r} must be an object")
        target_lane = _normalize_lane(str(raw_target.get("lane") or lane))
        if not target_lane:
            raise ValueError("worker probe lane may not be empty")
        targets[target_lane] = WorkerProbeTarget(
            lane=target_lane,
            api_url=_optional_string(raw_target.get("api_url")),
            api_token=_optional_string(raw_target.get("api_token")),
            ssh_host=_optional_string(raw_target.get("ssh_host")),
            ssh_user=_optional_string(raw_target.get("ssh_user")),
            ssh_port=_optional_int(raw_target.get("ssh_port")),
            service_name=_optional_string(raw_target.get("service_name"))
            or "enoch-control-plane",
            project_root=_optional_string(raw_target.get("project_root")),
            state_dir=_optional_string(raw_target.get("state_dir")),
            log_paths=_string_tuple(raw_target.get("log_paths")),
            ssh_timeout_seconds=_bounded_int(
                raw_target.get("ssh_timeout_seconds"), default=12, minimum=1, maximum=60
            ),
            api_timeout_seconds=_bounded_int(
                raw_target.get("api_timeout_seconds"), default=10, minimum=1, maximum=60
            ),
        )
    return targets


def _normalize_lane(value: str) -> str:
    normalized = value.strip().lower().replace("_worker", "")
    if normalized == "gpu":
        return "gb10"
    return normalized


def _optional_string(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _optional_int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    return int(value)


def _bounded_int(value: Any, *, default: int, minimum: int, maximum: int) -> int:
    if value is None or value == "":
        return default
    number = int(value)
    return max(minimum, min(maximum, number))


def _string_tuple(value: Any) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, str):
        return (value,)
    if not isinstance(value, (list, tuple)):
        raise ValueError("log_paths must be a string or list of strings")
    return tuple(str(item) for item in value if str(item).strip())
