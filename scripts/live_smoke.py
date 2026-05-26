"""Live smoke test for an Enoch MCP server against a running Enoch control plane.

Usage:
    ENOCH_API_TOKEN=... uv run python scripts/live_smoke.py --api-url http://localhost:8787

The script exercises MCP tool registration plus read-only tools. It also calls only
safe mutating paths: dispatch dry-run, preflight, and Notion intake dry-run.
It never prints the bearer token.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
from typing import Any

from enoch_mcp.config import DEFAULT_API_URL, EnochMCPConfig
from enoch_mcp.server import create_server


def unwrap(result: Any) -> Any:
    if isinstance(result, list) and result and hasattr(result[0], "text"):
        try:
            return json.loads(result[0].text)
        except Exception:  # noqa: BLE001 - smoke output only
            return result[0].text
    return result


def first_item(payload: Any) -> dict[str, Any] | None:
    payload = unwrap(payload)
    if isinstance(payload, dict):
        for key in ("items", "rows", "papers", "reviews", "queue", "data"):
            value = payload.get(key)
            if isinstance(value, list) and value and isinstance(value[0], dict):
                return value[0]
        for value in payload.values():
            if isinstance(value, list) and value and isinstance(value[0], dict):
                return value[0]
    if isinstance(payload, list) and payload and isinstance(payload[0], dict):
        return payload[0]
    return None


async def run_smoke(api_url: str, token: str) -> int:
    server = create_server(EnochMCPConfig(api_url=api_url, api_token=token))
    registered = await server.list_tools()
    print(f"REGISTERED_TOOLS {len(registered)}")
    print(
        "MUTATING_APPROVAL_META "
        f"{sum(1 for tool in registered if tool.meta == {'userApproval': 'required'})}"
    )

    failures: list[str] = []

    async def run(name: str, args: dict[str, Any] | None = None, *, required: bool = True) -> Any:
        try:
            result = unwrap(await server.call_tool(name, args or {}))
            summary = ""
            if isinstance(result, dict):
                summary = " keys=" + ",".join(list(result.keys())[:8])
            print(f"PASS {name}{summary}")
            return result
        except Exception as exc:  # noqa: BLE001 - smoke script reports failures
            message = f"{name}: {type(exc).__name__}: {exc}"
            if required:
                failures.append(message)
                print(f"FAIL {message}")
            else:
                print(f"SKIP_FAIL {message}")
            return None

    await run("enoch_core_health")
    overview = await run("enoch_overview", {"active_limit": 5, "event_limit": 5})
    await run("enoch_automation_readiness")
    await run("enoch_research_quality")
    await run("enoch_intake_status", {"page_size": 5})
    lanes = await run("enoch_lanes")
    if os.environ.get("ENOCH_WORKER_PROBES_JSON") or os.environ.get("ENOCH_WORKER_PROBES_FILE"):
        await run("enoch_probe_worker", {"lane": "cpu"}, required=False)
        await run("enoch_probe_worker", {"lane": "gb10"}, required=False)
        await run(
            "enoch_worker_logs",
            {"lane": "gb10", "log_kind": "service", "lines": 20},
            required=False,
        )
    else:
        print("SKIP worker direct probes no ENOCH_WORKER_PROBES_JSON/FILE configured")
    await run("enoch_status", {"refresh_worker": False})
    await run("enoch_queue_health", {"refresh_worker": False})
    for status in ("active", "queued", "blocked", "paused"):
        await run("enoch_queue_list", {"status": status, "page_size": 5})
    await run("enoch_v1_queue", {"queue": "all", "page_size": 5})
    projects = await run("enoch_projects", {"page_size": 5})
    runs = await run("enoch_runs", {"page_size": 5})
    papers = await run("enoch_papers_list", {"page": 1, "page_size": 5})
    await run("enoch_reviews_list", {"page": 1, "page_size": 5})
    await run("enoch_review_next", required=False)
    await run("enoch_events", {"page_size": 5})
    await run("enoch_core_queue_projection")
    await run("enoch_core_paper_candidates", {"kind": "draft"}, required=False)
    await run("enoch_core_paper_candidates", {"kind": "polish"}, required=False)

    project = first_item(projects)
    if project and project.get("project_id"):
        await run(
            "enoch_project_detail",
            {"project_id": str(project["project_id"]), "event_limit": 5},
        )
    else:
        print("SKIP enoch_project_detail no project id found")

    run_item = first_item(runs)
    if run_item and run_item.get("run_id"):
        await run("enoch_run_detail", {"run_id": str(run_item["run_id"]), "event_limit": 5})
    else:
        print("SKIP enoch_run_detail no run id found")

    paper = first_item(papers)
    paper_id = None
    if paper:
        for key in ("paper_id", "id"):
            if paper.get(key):
                paper_id = str(paper[key])
                break
    if paper_id:
        detail = await run("enoch_paper_detail", {"paper_id": paper_id})
        detail_obj = unwrap(detail)
        fields = [
            "draft_markdown_path",
            "draft_latex_path",
            "evidence_bundle_path",
            "claim_ledger_path",
            "manifest_path",
        ]
        candidates = [paper]
        if isinstance(detail_obj, dict):
            candidates.append(detail_obj)
            candidates.extend(value for value in detail_obj.values() if isinstance(value, dict))
        artifact_field = next(
            (field for candidate in candidates for field in fields if candidate.get(field)), None
        )
        if artifact_field:
            await run("enoch_paper_artifact", {"paper_id": paper_id, "field": artifact_field})
        else:
            print("SKIP enoch_paper_artifact no artifact path found in first paper")
    else:
        print("SKIP enoch_paper_detail/enoch_paper_artifact no paper id found")

    await run(
        "enoch_dispatch",
        {"requested_by": "enoch-mcp-live-smoke", "dry_run": True, "force_preflight": False},
        required=False,
    )
    lane_candidate = None
    for payload in (lanes, overview):
        payload = unwrap(payload)
        if isinstance(payload, dict):
            lane_candidate = payload.get("next_candidate")
            if isinstance(lane_candidate, dict) and lane_candidate.get("project_id"):
                break
            lane_candidate = None
    if lane_candidate:
        await run(
            "enoch_dispatch_one",
            {
                "project_id": str(lane_candidate["project_id"]),
                "requested_by": "enoch-mcp-live-smoke",
                "dry_run": True,
            },
            required=False,
        )
    else:
        print("SKIP enoch_dispatch_one no lane candidate found")
    await run(
        "enoch_queue_alert_check",
        {"requested_by": "enoch-mcp-live-smoke", "dry_run": True, "refresh_worker": False},
        required=False,
    )
    await run(
        "enoch_reconcile_stale_lane",
        {"requested_by": "enoch-mcp-live-smoke", "dry_run": True, "refresh_worker": False},
        required=False,
    )
    await run(
        "enoch_research_run_cycle",
        {"requested_by": "enoch-mcp-live-smoke", "dry_run": True, "refresh_worker": False},
        required=False,
    )
    await run(
        "enoch_launch_followup",
        {"requested_by": "enoch-mcp-live-smoke", "dry_run": True},
        required=False,
    )
    await run("enoch_preflight", {"payload": {}}, required=False)
    await run(
        "enoch_intake_notion",
        {"ideas": [], "source": "enoch-mcp-live-smoke", "dry_run": True},
        required=False,
    )
    await run(
        "enoch_intake_ideas",
        {"ideas": [], "source": "enoch-mcp-live-smoke", "dry_run": True},
        required=False,
    )
    await run(
        "enoch_draft_paper",
        {"requested_by": "enoch-mcp-live-smoke", "dry_run": True},
        required=False,
    )

    if failures:
        print("SUMMARY FAIL")
        for failure in failures:
            print(f" - {failure}")
        return 1
    print("SUMMARY PASS")
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="Run live Enoch MCP smoke checks.")
    parser.add_argument("--api-url", default=os.environ.get("ENOCH_API_URL", DEFAULT_API_URL))
    args = parser.parse_args()
    token = os.environ.get("ENOCH_API_TOKEN")
    if not token:
        raise SystemExit("ENOCH_API_TOKEN is required")
    raise SystemExit(asyncio.run(run_smoke(args.api_url, token)))


if __name__ == "__main__":
    main()
