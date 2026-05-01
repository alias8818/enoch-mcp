"""Read-only MCP tool implementations for Enoch."""

from __future__ import annotations

from typing import Any, Literal

from .client import EnochClient

QueueStatus = Literal["active", "queued", "blocked", "paused"]
ArtifactField = Literal[
    "draft_markdown_path",
    "draft_latex_path",
    "evidence_bundle_path",
    "claim_ledger_path",
    "manifest_path",
]
CandidateKind = Literal["draft", "polish"]


async def enoch_status(client: EnochClient, refresh_worker: bool = True) -> Any:
    """Return full system status including dispatch safety, counts, warnings, and conflicts."""
    return await client.get("/control/api/status", {"refresh_worker": refresh_worker})


async def enoch_queue_health(client: EnochClient, refresh_worker: bool = True) -> Any:
    """Return queue health, worker freshness, alert findings, and recent events."""
    return await client.get("/control/api/queue-health", {"refresh_worker": refresh_worker})


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
    entity_type: str | None = None,
    entity_id: str | None = None,
    event_type: str | None = None,
    search: str | None = None,
    page: int = 1,
    page_size: int = 100,
) -> Any:
    """Query the Enoch event log."""
    return await client.get(
        "/control/api/events",
        {
            "page": page,
            "page_size": page_size,
            "entity_type": entity_type,
            "entity_id": entity_id,
            "event_type": event_type,
            "search": search,
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
