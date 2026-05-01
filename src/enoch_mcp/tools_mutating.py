"""Mutating MCP tool implementations for Enoch."""

from __future__ import annotations

from typing import Any, Literal

from .client import EnochClient

ChecklistStatus = Literal["pass", "fail", "accepted_risk"]


async def enoch_dispatch(
    client: EnochClient,
    requested_by: str,
    dry_run: bool = True,
    force_preflight: bool = False,
) -> Any:
    """Dispatch the next queued item. Defaults to dry_run=True for safety."""
    return await client.post(
        "/control/dispatch-next",
        {"requested_by": requested_by, "dry_run": dry_run, "force_preflight": force_preflight},
    )


async def enoch_pause(
    client: EnochClient,
    reason: str,
    paused_by: str = "mcp",
    maintenance_mode: bool = False,
) -> Any:
    """Pause the Enoch queue."""
    return await client.post(
        "/control/pause",
        {"reason": reason, "paused_by": paused_by, "maintenance_mode": maintenance_mode},
    )


async def enoch_resume(
    client: EnochClient,
    resumed_by: str = "mcp",
    maintenance_mode: bool = False,
) -> Any:
    """Resume the Enoch queue."""
    return await client.post(
        "/control/resume", {"resumed_by": resumed_by, "maintenance_mode": maintenance_mode}
    )


async def enoch_preflight(client: EnochClient, payload: dict[str, Any] | None = None) -> Any:
    """Run a worker health preflight check."""
    return await client.post("/control/worker/preflight", payload or {})


async def enoch_intake_notion(
    client: EnochClient,
    ideas: list[dict[str, Any]],
    idempotency_key: str | None = None,
    source: str = "mcp",
    dry_run: bool = True,
) -> Any:
    """Ingest Notion ideas. Defaults to dry_run=True for safety."""
    return await client.post(
        "/control/intake/notion-ideas",
        {
            "idempotency_key": idempotency_key,
            "source": source,
            "ideas": ideas,
            "dry_run": dry_run,
        },
    )


async def enoch_review_claim(client: EnochClient, paper_id: str, claimed_by: str) -> Any:
    """Claim a paper review."""
    return await client.post(
        f"/control/api/paper-reviews/{paper_id}/claim", {"claimed_by": claimed_by}
    )


async def enoch_review_checklist(
    client: EnochClient,
    paper_id: str,
    item_id: str,
    status: ChecklistStatus,
    note: str | None = None,
) -> Any:
    """Update a publication review checklist item."""
    return await client.post(
        f"/control/api/paper-reviews/{paper_id}/checklist/{item_id}",
        {"status": status, "note": note},
    )


async def enoch_review_status(
    client: EnochClient,
    paper_id: str,
    review_status: str,
    updated_by: str = "mcp",
) -> Any:
    """Update paper review status."""
    return await client.post(
        f"/control/api/paper-reviews/{paper_id}/status",
        {"review_status": review_status, "updated_by": updated_by},
    )


async def enoch_draft_paper(client: EnochClient, requested_by: str, force: bool = False) -> Any:
    """Draft the next eligible paper."""
    return await client.post(
        "/control/papers/draft-next", {"requested_by": requested_by, "force": force}
    )


async def enoch_rewrite_draft(
    client: EnochClient, paper_id: str, requested_by: str, force: bool = False
) -> Any:
    """Rewrite a paper draft through Enoch's API."""
    return await client.post(
        f"/control/api/paper-reviews/{paper_id}/rewrite-draft",
        {"requested_by": requested_by, "force": force},
    )
