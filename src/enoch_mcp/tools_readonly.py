"""Read-only MCP tool implementations for Enoch."""

from __future__ import annotations

from typing import Any, Literal

from . import worker_probe
from .client import EnochClient

QueueStatus = Literal["active", "queued", "blocked", "paused"]
V1Queue = Literal["all", "active", "queued", "blocked", "paused"]
ArtifactField = Literal[
    "draft_markdown_path",
    "draft_latex_path",
    "evidence_bundle_path",
    "claim_ledger_path",
    "manifest_path",
]
CandidateKind = Literal["draft", "polish"]
WorkerLane = worker_probe.WorkerLane
WorkerLogKind = worker_probe.WorkerLogKind


async def enoch_status(client: EnochClient, refresh_worker: bool = True) -> Any:
    """Return full system status including dispatch safety, counts, warnings, and conflicts."""
    return await client.get("/control/api/status", {"refresh_worker": refresh_worker})


async def enoch_queue_health(client: EnochClient, refresh_worker: bool = True) -> Any:
    """Return queue health, worker freshness, alert findings, and recent events."""
    return await client.get("/control/api/queue-health", {"refresh_worker": refresh_worker})


async def enoch_overview(
    client: EnochClient, active_limit: int = 5, event_limit: int = 10
) -> Any:
    """Return the bounded Dashboard V1 overview read model."""
    return await client.get(
        "/control/api/v1/overview",
        {"active_limit": active_limit, "event_limit": event_limit},
    )


async def enoch_automation_readiness(client: EnochClient) -> Any:
    """Return the canonical long-haul automation readiness check."""
    return await client.get("/control/api/v1/automation-readiness")


async def enoch_research_quality(client: EnochClient) -> Any:
    """Return the latest research quality readiness report."""
    return await client.get("/control/api/v1/research-quality")


async def enoch_intake_status(
    client: EnochClient, page_size: int = 50, include_latest_payload: bool = False
) -> Any:
    """Return current control-plane idea intake status."""
    return await client.get(
        "/control/api/intake/ideas",
        {"page_size": page_size, "include_latest_payload": include_latest_payload},
    )


async def enoch_lanes(client: EnochClient) -> Any:
    """Return bounded active worker lane state and lane-aware next candidate."""
    return await client.get("/control/api/v1/lanes")


async def enoch_probe_worker(
    client: EnochClient,
    lane: WorkerLane | None = None,
    run_id: str | None = None,
) -> Any:
    """Probe a configured worker lane through API-first diagnostics and SSH fallback."""
    return await worker_probe.probe_worker(client.config, lane=lane, run_id=run_id)


async def enoch_worker_logs(
    client: EnochClient,
    lane: WorkerLane | None = None,
    log_kind: WorkerLogKind = "service",
    run_id: str | None = None,
    lines: int = 80,
) -> Any:
    """Return bounded allowlisted worker log tails."""
    return await worker_probe.worker_logs(
        client.config, lane=lane, log_kind=log_kind, run_id=run_id, lines=lines
    )


async def enoch_worker_artifacts(
    client: EnochClient,
    lane: WorkerLane | None = None,
    project_id: str | None = None,
    run_id: str | None = None,
) -> Any:
    """Check expected worker artifact presence without dumping arbitrary files."""
    return await worker_probe.worker_artifacts(
        client.config, lane=lane, project_id=project_id, run_id=run_id
    )


async def enoch_queue_list(
    client: EnochClient,
    status: QueueStatus,
    search: str | None = None,
    page_size: int = 100,
) -> Any:
    """List queue items by status."""
    return await client.get(
        f"/control/api/queues/{status}", {"page_size": page_size, "search": search}
    )


async def enoch_v1_queue(
    client: EnochClient,
    queue: V1Queue = "all",
    status: str = "",
    search: str = "",
    cursor: str = "",
    page_size: int = 50,
    sort: str = "priority",
) -> Any:
    """List queue rows through the bounded Dashboard V1 read model."""
    return await client.get(
        "/control/api/v1/queue",
        {
            "queue": queue,
            "status": status,
            "search": search,
            "cursor": cursor,
            "page_size": page_size,
            "sort": sort,
        },
    )


async def enoch_projects(
    client: EnochClient,
    status: str = "",
    search: str = "",
    cursor: str = "",
    page_size: int = 50,
    sort: str = "recent",
) -> Any:
    """List projects through the bounded Dashboard V1 read model."""
    return await client.get(
        "/control/api/v1/projects",
        {
            "status": status,
            "search": search,
            "cursor": cursor,
            "page_size": page_size,
            "sort": sort,
        },
    )


async def enoch_project_detail(
    client: EnochClient, project_id: str, event_limit: int = 50
) -> Any:
    """Return bounded project detail, related queue/run/paper rows, and events."""
    return await client.get(
        f"/control/api/v1/projects/{project_id}", {"event_limit": event_limit}
    )


async def enoch_runs(
    client: EnochClient,
    state: str = "",
    project_id: str = "",
    search: str = "",
    cursor: str = "",
    page_size: int = 50,
    sort: str = "recent",
) -> Any:
    """List runs through the bounded Dashboard V1 read model."""
    return await client.get(
        "/control/api/v1/runs",
        {
            "state": state,
            "project_id": project_id,
            "search": search,
            "cursor": cursor,
            "page_size": page_size,
            "sort": sort,
        },
    )


async def enoch_run_detail(client: EnochClient, run_id: str, event_limit: int = 50) -> Any:
    """Return bounded run detail, related queue/paper rows, and events."""
    return await client.get(f"/control/api/v1/runs/{run_id}", {"event_limit": event_limit})


async def enoch_papers_list(
    client: EnochClient,
    search: str | None = None,
    status: str | None = None,
    page: int = 1,
    page_size: int = 50,
    sort: str = "-updated_at",
) -> Any:
    """List papers with optional search/status filtering."""
    return await client.get(
        "/control/api/papers",
        {"page": page, "page_size": page_size, "search": search, "status": status, "sort": sort},
    )


async def enoch_paper_detail(client: EnochClient, paper_id: str) -> Any:
    """Get paper detail with project, run, events, warnings, and artifact status."""
    return await client.get(f"/control/api/papers/{paper_id}")


async def enoch_paper_artifact(client: EnochClient, paper_id: str, field: ArtifactField) -> Any:
    """Read a paper artifact through the Enoch API."""
    return await client.get(f"/control/api/papers/{paper_id}/artifact/{field}")


async def enoch_reviews_list(
    client: EnochClient,
    review_status: str | None = None,
    paper_status: str | None = None,
    search: str | None = None,
    page: int = 1,
    page_size: int = 100,
    include_rank_reasons: bool = True,
) -> Any:
    """List publication reviews and checklist/ranking metadata."""
    return await client.get(
        "/control/api/paper-reviews",
        {
            "page": page,
            "page_size": page_size,
            "search": search,
            "review_status": review_status,
            "paper_status": paper_status,
            "include_rank_reasons": include_rank_reasons,
        },
    )


async def enoch_review_next(client: EnochClient, paper_status: str = "publication_draft") -> Any:
    """Return the next unreviewed paper candidate."""
    return await client.get("/control/api/paper-reviews/next", {"paper_status": paper_status})


async def enoch_events(
    client: EnochClient,
    event_id: str | None = None,
    entity_type: str | None = None,
    entity_id: str | None = None,
    event_type: str | None = None,
    search: str | None = None,
    cursor: str = "",
    page_size: int = 50,
    include_payload: bool = False,
    sort: str = "recent",
) -> Any:
    """Query the bounded Dashboard V1 Enoch event log."""
    return await client.get(
        "/control/api/v1/events",
        {
            "event_id": event_id,
            "page_size": page_size,
            "entity_type": entity_type,
            "entity_id": entity_id,
            "event_type": event_type,
            "search": search,
            "cursor": cursor,
            "include_payload": include_payload,
            "sort": sort,
        },
    )


async def enoch_core_health(client: EnochClient) -> Any:
    """Return Enoch core health and operating mode."""
    return await client.get("/enoch-core/health")


async def enoch_core_queue_projection(client: EnochClient, mode: str | None = None) -> Any:
    """Return Enoch core queue projection."""
    return await client.get("/enoch-core/projections/queue", {"mode": mode})


async def enoch_core_paper_candidates(
    client: EnochClient, kind: CandidateKind, mode: str | None = None
) -> Any:
    """Return next paper draft or polish candidate from Enoch core."""
    suffix = "paper-draft" if kind == "draft" else "paper-polish"
    return await client.get(f"/enoch-core/candidates/{suffix}", {"mode": mode})
