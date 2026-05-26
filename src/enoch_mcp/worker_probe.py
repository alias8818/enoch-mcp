"""Optional direct worker diagnostics for Enoch MCP.

This module intentionally exposes named diagnostics, not a raw shell surface.
SSH commands are fixed templates with validated inputs and bounded output.
"""

from __future__ import annotations

import asyncio
import re
import shlex
from dataclasses import asdict
from typing import Any, Literal

import httpx

from .config import EnochMCPConfig, WorkerProbeTarget

WorkerLane = Literal["cpu", "gpu", "gb10"]
WorkerLogKind = Literal["service", "wake_gate", "active_run"]

_SAFE_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:+-]{0,220}$")
_SAFE_SERVICE_RE = re.compile(r"^[A-Za-z0-9_.@:+-]{1,120}$")
_MAX_OUTPUT_BYTES = 80_000


async def probe_worker(
    config: EnochMCPConfig,
    *,
    lane: WorkerLane | None = None,
    run_id: str | None = None,
) -> dict[str, Any]:
    """Probe a configured worker lane with API-first diagnostics and SSH fallback."""
    normalized_lane = _normalize_lane(lane)
    target = _select_target(config, normalized_lane)
    if run_id:
        _validate_identifier(run_id, "run_id")
    if target is None:
        return _not_configured(config, normalized_lane)

    api = await _api_probe(target, run_id=run_id)
    ssh = await _ssh_probe(target, run_id=run_id)
    return {
        "ok": api.get("ok") is True or ssh.get("ok") is True,
        "source": "enoch_mcp_worker_probe",
        "lane": target.lane,
        "run_id": run_id,
        "target": _public_target(target),
        "api": api,
        "ssh": ssh,
    }


async def worker_logs(
    config: EnochMCPConfig,
    *,
    lane: WorkerLane | None = None,
    log_kind: WorkerLogKind = "service",
    run_id: str | None = None,
    lines: int = 80,
) -> dict[str, Any]:
    """Return bounded allowlisted worker log tails."""
    normalized_lane = _normalize_lane(lane)
    target = _select_target(config, normalized_lane)
    safe_lines = _bounded_lines(lines)
    if run_id:
        _validate_identifier(run_id, "run_id")
    if target is None:
        return _not_configured(config, normalized_lane)
    if not target.ssh_host:
        return {
            "ok": False,
            "source": "enoch_mcp_worker_logs",
            "lane": target.lane,
            "reason": "worker target has no ssh_host configured",
            "target": _public_target(target),
        }
    command = _log_command(target, log_kind=log_kind, run_id=run_id, lines=safe_lines)
    if command is None:
        return {
            "ok": False,
            "source": "enoch_mcp_worker_logs",
            "lane": target.lane,
            "log_kind": log_kind,
            "reason": "active_run logs require run_id and project_root",
            "target": _public_target(target),
        }
    result = await _run_ssh(target, command)
    return {
        "ok": result["exit_code"] == 0,
        "source": "enoch_mcp_worker_logs",
        "lane": target.lane,
        "log_kind": log_kind,
        "lines": safe_lines,
        "target": _public_target(target),
        "result": result,
    }


async def worker_artifacts(
    config: EnochMCPConfig,
    *,
    lane: WorkerLane | None = None,
    project_id: str | None = None,
    run_id: str | None = None,
) -> dict[str, Any]:
    """Check expected worker artifact presence without dumping arbitrary files."""
    normalized_lane = _normalize_lane(lane)
    target = _select_target(config, normalized_lane)
    if project_id:
        _validate_identifier(project_id, "project_id")
    if run_id:
        _validate_identifier(run_id, "run_id")
    if target is None:
        return _not_configured(config, normalized_lane)

    api: dict[str, Any] = {"ok": False, "reason": "worker target has no api_url configured"}
    if target.api_url and project_id:
        api = await _api_project_status(target, project_id=project_id, run_id=run_id)
    elif target.api_url:
        api = {"ok": False, "reason": "project_id is required for API artifact probe"}

    ssh: dict[str, Any] = {"ok": False, "reason": "worker target has no ssh_host configured"}
    if target.ssh_host and target.project_root and project_id:
        ssh = await _ssh_artifact_probe(target, project_id=project_id, run_id=run_id)
    elif target.ssh_host:
        ssh = {"ok": False, "reason": "project_id and project_root are required for SSH probe"}

    return {
        "ok": api.get("ok") is True or ssh.get("ok") is True,
        "source": "enoch_mcp_worker_artifacts",
        "lane": target.lane,
        "project_id": project_id,
        "run_id": run_id,
        "target": _public_target(target),
        "api": api,
        "ssh": ssh,
    }


def _normalize_lane(lane: str | None) -> str | None:
    if lane is None:
        return None
    value = lane.strip().lower().replace("_worker", "")
    if value == "gpu":
        return "gb10"
    return value or None


def _select_target(config: EnochMCPConfig, lane: str | None) -> WorkerProbeTarget | None:
    targets = config.resolved_worker_probe_targets
    if not targets:
        return None
    if lane:
        return targets.get(lane)
    if len(targets) == 1:
        return next(iter(targets.values()))
    return None


def _not_configured(config: EnochMCPConfig, lane: str | None) -> dict[str, Any]:
    targets = sorted(config.resolved_worker_probe_targets)
    reason = (
        "no worker probe targets configured"
        if not targets
        else "lane is required when multiple worker probe targets are configured"
    )
    if lane and targets and lane not in targets:
        reason = f"worker probe lane is not configured: {lane}"
    return {
        "ok": False,
        "source": "enoch_mcp_worker_probe",
        "lane": lane,
        "reason": reason,
        "configured_lanes": targets,
    }


async def _api_probe(target: WorkerProbeTarget, *, run_id: str | None) -> dict[str, Any]:
    if not target.api_url:
        return {"ok": False, "reason": "worker target has no api_url configured"}
    out: dict[str, Any] = {"ok": False, "base_url": target.api_url.rstrip("/")}
    async with httpx.AsyncClient(
        base_url=target.api_url.rstrip("/"), timeout=target.api_timeout_seconds
    ) as client:
        headers = _api_headers(target)
        out["healthz"] = await _safe_get(client, "/healthz")
        dashboard = await _safe_get(
            client,
            "/dashboard/api",
            headers=headers,
            params={"limit": 20, "event_limit": 20, "detail": False},
        )
        out["dashboard"] = _summarize_dashboard(dashboard, run_id=run_id)
        if run_id:
            out["run"] = await _safe_get(client, f"/dashboard/api/run/{run_id}", headers=headers)
    out["ok"] = bool(out.get("healthz", {}).get("ok")) or bool(
        out.get("dashboard", {}).get("ok")
    )
    return out


async def _api_project_status(
    target: WorkerProbeTarget, *, project_id: str, run_id: str | None
) -> dict[str, Any]:
    async with httpx.AsyncClient(
        base_url=(target.api_url or "").rstrip("/"), timeout=target.api_timeout_seconds
    ) as client:
        payload = await _safe_get(
            client,
            f"/project-status/{project_id}",
            headers=_api_headers(target),
            params={"run_id": run_id} if run_id else None,
        )
    return _summarize_project_status(payload)


async def _safe_get(
    client: httpx.AsyncClient,
    path: str,
    *,
    headers: dict[str, str] | None = None,
    params: dict[str, Any] | None = None,
) -> dict[str, Any]:
    try:
        response = await client.get(path, headers=headers, params=params)
        response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        return {
            "ok": False,
            "status_code": exc.response.status_code,
            "error": _truncate(exc.response.text.strip(), 2000),
        }
    except httpx.HTTPError as exc:
        return {"ok": False, "error": str(exc)}
    try:
        data = response.json()
    except ValueError:
        return {"ok": True, "status_code": response.status_code, "content": response.text[:2000]}
    if isinstance(data, dict):
        data.setdefault("ok", True)
        return data
    return {"ok": True, "data": data}


def _api_headers(target: WorkerProbeTarget) -> dict[str, str] | None:
    if not target.api_token:
        return None
    return {"Authorization": f"Bearer {target.api_token}"}


def _summarize_dashboard(payload: dict[str, Any], *, run_id: str | None) -> dict[str, Any]:
    if not payload.get("ok"):
        return payload
    runs = payload.get("runs") if isinstance(payload.get("runs"), list) else []
    matching = [
        _compact_mapping(item)
        for item in runs
        if isinstance(item, dict) and run_id and str(item.get("run_id") or "") == run_id
    ]
    return {
        "ok": True,
        "timestamp": payload.get("timestamp"),
        "service": _compact_mapping(payload.get("service")),
        "totals": payload.get("totals"),
        "telemetry": payload.get("telemetry"),
        "matching_run_present": bool(matching),
        "matching_runs": matching[:3],
    }


def _summarize_project_status(payload: dict[str, Any]) -> dict[str, Any]:
    if not payload.get("ok", True) or "error" in payload:
        return payload
    result_files = (
        payload.get("result_files") if isinstance(payload.get("result_files"), list) else []
    )
    recent_files = (
        payload.get("recent_files") if isinstance(payload.get("recent_files"), list) else []
    )
    expected_names = {
        "project_decision.json",
        "evidence_bundle.json",
        "claim_ledger.json",
        "manifest.json",
        "result.md",
        "run_notes.md",
    }
    observed = [
        str(item.get("path") or item.get("name") or item)
        for item in [*result_files, *recent_files]
        if isinstance(item, (dict, str))
    ]
    return {
        "ok": True,
        "timestamp": payload.get("timestamp"),
        "project_id": payload.get("project_id"),
        "project_dir": payload.get("project_dir"),
        "run": _compact_mapping(payload.get("run")),
        "latest_session": _compact_mapping(payload.get("latest_session")),
        "expected_artifacts": {
            name: any(path.endswith(name) for path in observed) for name in sorted(expected_names)
        },
        "result_files": result_files[:20],
        "recent_files": recent_files[:20],
    }


async def _ssh_probe(target: WorkerProbeTarget, *, run_id: str | None) -> dict[str, Any]:
    if not target.ssh_host:
        return {"ok": False, "reason": "worker target has no ssh_host configured"}
    commands: dict[str, str] = {
        "service": _service_command(target),
        "disk": _disk_command(target),
        "processes": _process_command(run_id=run_id),
    }
    results = {name: await _run_ssh(target, command) for name, command in commands.items()}
    return {
        "ok": any(item["exit_code"] == 0 for item in results.values()),
        "results": results,
    }


async def _ssh_artifact_probe(
    target: WorkerProbeTarget, *, project_id: str, run_id: str | None
) -> dict[str, Any]:
    project_root = target.project_root
    if not project_root:
        return {"ok": False, "reason": "project_root is not configured"}
    expected = [
        ".enoch/project_decision.json",
        "evidence_bundle.json",
        "claim_ledger.json",
        "manifest.json",
        "result.md",
        "run_notes.md",
    ]
    tests = []
    for relative in expected:
        path = f"{project_root.rstrip('/')}/{project_id}/{relative}"
        tests.append(
            f"if test -e {shlex.quote(path)}; "
            f"then echo present:{shlex.quote(relative)}; "
            f"else echo missing:{shlex.quote(relative)}; fi"
        )
    if run_id:
        tests.append(
            "find "
            f"{shlex.quote(project_root)} -maxdepth 4 -type f -path "
            f"{shlex.quote('*' + run_id + '*')} -print | head -20"
        )
    result = await _run_ssh(target, " ; ".join(tests))
    present = {}
    for line in result["stdout"].splitlines():
        if line.startswith("present:"):
            present[line.removeprefix("present:")] = True
        if line.startswith("missing:"):
            present[line.removeprefix("missing:")] = False
    return {"ok": result["exit_code"] == 0, "expected_artifacts": present, "result": result}


def _service_command(target: WorkerProbeTarget) -> str:
    service = _safe_service(target.service_name)
    return (
        f"systemctl is-active {shlex.quote(service)}; "
        f"systemctl show {shlex.quote(service)} "
        "--property=ActiveState --property=SubState --property=MainPID "
        "--property=FragmentPath --no-pager"
    )


def _disk_command(target: WorkerProbeTarget) -> str:
    path = target.project_root or target.state_dir or "/"
    return f"df -Pk {shlex.quote(path)}"


def _process_command(*, run_id: str | None) -> str:
    if run_id:
        pattern = run_id
    else:
        pattern = "enoch|omx|codex|python|node|uvicorn"
    return f"pgrep -af {shlex.quote(pattern)} | head -40"


def _log_command(
    target: WorkerProbeTarget, *, log_kind: WorkerLogKind, run_id: str | None, lines: int
) -> str | None:
    if log_kind == "service":
        service = _safe_service(target.service_name)
        return f"journalctl -u {shlex.quote(service)} -n {lines} --no-pager -o short-iso"
    if log_kind == "wake_gate":
        paths = target.log_paths or (
            "/var/log/enoch-control-plane.log",
            "/var/log/enoch/worker.log",
        )
        checks = [
            f"if test -r {shlex.quote(path)}; "
            f"then echo '== {path} =='; tail -n {lines} {shlex.quote(path)}; fi"
            for path in paths
        ]
        return " ; ".join(checks)
    if not run_id or not target.project_root:
        return None
    pattern = "*" + run_id + "*"
    return (
        "file=$(find "
        f"{shlex.quote(target.project_root)} -maxdepth 5 -type f "
        "\\( -name '*.log' -o -name 'run_notes.md' -o -name 'events.jsonl' \\) "
        f"-path {shlex.quote(pattern)} -print -quit); "
        "if test -n \"$file\"; then echo \"== $file ==\"; tail -n "
        f"{lines} \"$file\"; else echo 'no active_run log found'; exit 1; fi"
    )


async def _run_ssh(target: WorkerProbeTarget, remote_command: str) -> dict[str, Any]:
    host = _ssh_destination(target)
    args = [
        "ssh",
        "-n",
        "-o",
        "BatchMode=yes",
        "-o",
        "ConnectTimeout=5",
        "-o",
        "StrictHostKeyChecking=accept-new",
    ]
    if target.ssh_port:
        args.extend(["-p", str(target.ssh_port)])
    args.extend([host, "--", f"/bin/sh -c {shlex.quote(remote_command)}"])
    try:
        process = await asyncio.create_subprocess_exec(
            *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(
            process.communicate(), timeout=target.ssh_timeout_seconds
        )
    except TimeoutError:
        process.kill()
        await process.wait()
        return {"exit_code": None, "timed_out": True, "stdout": "", "stderr": "ssh timed out"}
    except OSError as exc:
        return {"exit_code": None, "error": str(exc), "stdout": "", "stderr": ""}
    return {
        "exit_code": process.returncode,
        "timed_out": False,
        "stdout": _decode(stdout),
        "stderr": _decode(stderr),
    }


def _ssh_destination(target: WorkerProbeTarget) -> str:
    if not target.ssh_host:
        raise ValueError("ssh_host is required")
    return f"{target.ssh_user}@{target.ssh_host}" if target.ssh_user else target.ssh_host


def _validate_identifier(value: str, label: str) -> None:
    if not _SAFE_ID_RE.fullmatch(value):
        raise ValueError(f"{label} contains unsupported characters")


def _safe_service(value: str) -> str:
    if not _SAFE_SERVICE_RE.fullmatch(value):
        raise ValueError("service_name contains unsupported characters")
    return value


def _bounded_lines(lines: int) -> int:
    return max(1, min(200, int(lines)))


def _decode(value: bytes) -> str:
    return _truncate(value.decode("utf-8", errors="replace"), _MAX_OUTPUT_BYTES)


def _truncate(value: str, limit: int) -> str:
    if len(value) <= limit:
        return value
    return value[:limit] + "\n...[truncated]"


def _compact_mapping(value: Any) -> dict[str, Any] | None:
    if not isinstance(value, dict):
        return None
    allowed = {
        "run_id",
        "project_id",
        "project_name",
        "status",
        "state",
        "lifecycle_state",
        "gate_state",
        "is_live",
        "needs_attention",
        "last_event_at",
        "updated_at",
        "created_at",
        "name",
        "listen_host",
        "listen_port",
        "state_dir",
        "project_root",
    }
    return {key: item for key, item in value.items() if key in allowed}


def _public_target(target: WorkerProbeTarget) -> dict[str, Any]:
    data = asdict(target)
    data.pop("api_token", None)
    return data
