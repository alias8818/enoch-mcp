"""MCP server setup and tool registration."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations

from . import tools_mutating as mutating
from . import tools_readonly as readonly
from .client import EnochAPIError, EnochClient
from .config import EnochMCPConfig

ClientFactory = Callable[[], EnochClient]


def readonly_annotations(title: str) -> ToolAnnotations:
    return ToolAnnotations(
        title=title,
        readOnlyHint=True,
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=True,
    )


def mutating_annotations(
    title: str, *, destructive: bool = True, idempotent: bool = False
) -> ToolAnnotations:
    return ToolAnnotations(
        title=title,
        readOnlyHint=False,
        destructiveHint=destructive,
        idempotentHint=idempotent,
        openWorldHint=True,
    )


def default_client_factory(config: EnochMCPConfig) -> ClientFactory:
    return lambda: EnochClient(config)


def create_server(config: EnochMCPConfig, client_factory: ClientFactory | None = None) -> FastMCP:
    """Create and register the Enoch MCP server."""
    mcp = FastMCP("Enoch MCP")
    make_client = client_factory or default_client_factory(config)

    async def call_tool(func: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        try:
            async with make_client() as client:
                return await func(client, *args, **kwargs)
        except EnochAPIError as exc:
            raise RuntimeError(str(exc)) from exc

    @mcp.tool(annotations=readonly_annotations("Enoch Status"))
    async def enoch_status(refresh_worker: bool = True) -> Any:
        """Full system status: dispatch safety, flags, counts, active items, warnings, conflicts."""
        return await call_tool(readonly.enoch_status, refresh_worker=refresh_worker)

    @mcp.tool(annotations=readonly_annotations("Enoch Queue Health"))
    async def enoch_queue_health(refresh_worker: bool = True) -> Any:
        """Queue health with worker freshness, alert findings, active runs, and recent events."""
        return await call_tool(readonly.enoch_queue_health, refresh_worker=refresh_worker)

    @mcp.tool(annotations=readonly_annotations("Enoch Queue List"))
    async def enoch_queue_list(
        status: readonly.QueueStatus, search: str | None = None, page_size: int = 100
    ) -> Any:
        """List queue items by status: active, queued, blocked, or paused."""
        return await call_tool(
            readonly.enoch_queue_list, status, search=search, page_size=page_size
        )

    @mcp.tool(annotations=readonly_annotations("Enoch Papers List"))
    async def enoch_papers_list(
        search: str | None = None,
        status: str | None = None,
        page: int = 1,
        page_size: int = 50,
        sort: str = "-updated_at",
    ) -> Any:
        """List papers with optional search/status filtering."""
        return await call_tool(
            readonly.enoch_papers_list,
            search=search,
            status=status,
            page=page,
            page_size=page_size,
            sort=sort,
        )

    @mcp.tool(annotations=readonly_annotations("Enoch Paper Detail"))
    async def enoch_paper_detail(paper_id: str) -> Any:
        """Get paper detail with project, run, events, warnings, and missing artifacts."""
        return await call_tool(readonly.enoch_paper_detail, paper_id)

    @mcp.tool(annotations=readonly_annotations("Enoch Paper Artifact"))
    async def enoch_paper_artifact(paper_id: str, field: readonly.ArtifactField) -> Any:
        """Read a paper artifact's content through the Enoch API."""
        return await call_tool(readonly.enoch_paper_artifact, paper_id, field)

    @mcp.tool(annotations=readonly_annotations("Enoch Reviews List"))
    async def enoch_reviews_list(
        review_status: str | None = None,
        paper_status: str | None = None,
        search: str | None = None,
        page: int = 1,
        page_size: int = 100,
        include_rank_reasons: bool = True,
    ) -> Any:
        """List publication reviews with checklist progress and rank scores."""
        return await call_tool(
            readonly.enoch_reviews_list,
            review_status=review_status,
            paper_status=paper_status,
            search=search,
            page=page,
            page_size=page_size,
            include_rank_reasons=include_rank_reasons,
        )

    @mcp.tool(annotations=readonly_annotations("Enoch Review Next"))
    async def enoch_review_next(paper_status: str = "publication_draft") -> Any:
        """Get the next unreviewed publication review candidate."""
        return await call_tool(readonly.enoch_review_next, paper_status=paper_status)

    @mcp.tool(annotations=readonly_annotations("Enoch Events"))
    async def enoch_events(
        entity_type: str | None = None,
        entity_id: str | None = None,
        event_type: str | None = None,
        search: str | None = None,
        page: int = 1,
        page_size: int = 100,
    ) -> Any:
        """Query the Enoch event log."""
        return await call_tool(
            readonly.enoch_events,
            entity_type=entity_type,
            entity_id=entity_id,
            event_type=event_type,
            search=search,
            page=page,
            page_size=page_size,
        )

    @mcp.tool(annotations=readonly_annotations("Enoch Core Health"))
    async def enoch_core_health() -> Any:
        """Get Enoch core health and operating mode."""
        return await call_tool(readonly.enoch_core_health)

    @mcp.tool(annotations=readonly_annotations("Enoch Core Queue Projection"))
    async def enoch_core_queue_projection(mode: str | None = None) -> Any:
        """Get Enoch core queue projection."""
        return await call_tool(readonly.enoch_core_queue_projection, mode=mode)

    @mcp.tool(annotations=readonly_annotations("Enoch Core Paper Candidates"))
    async def enoch_core_paper_candidates(
        kind: readonly.CandidateKind, mode: str | None = None
    ) -> Any:
        """Get the next paper draft or polish candidate from Enoch core."""
        return await call_tool(readonly.enoch_core_paper_candidates, kind, mode=mode)

    @mcp.tool(
        annotations=mutating_annotations("Enoch Dispatch", destructive=False),
        meta={"userApproval": "required"},
    )
    async def enoch_dispatch(
        requested_by: str, dry_run: bool = True, force_preflight: bool = False
    ) -> Any:
        """Dispatch the next queued item. Defaults to dry_run=True."""
        return await call_tool(
            mutating.enoch_dispatch,
            requested_by=requested_by,
            dry_run=dry_run,
            force_preflight=force_preflight,
        )

    @mcp.tool(
        annotations=mutating_annotations("Enoch Pause"),
        meta={"userApproval": "required"},
    )
    async def enoch_pause(
        reason: str, paused_by: str = "mcp", maintenance_mode: bool = False
    ) -> Any:
        """Pause the Enoch queue."""
        return await call_tool(
            mutating.enoch_pause,
            reason=reason,
            paused_by=paused_by,
            maintenance_mode=maintenance_mode,
        )

    @mcp.tool(
        annotations=mutating_annotations("Enoch Resume", destructive=False),
        meta={"userApproval": "required"},
    )
    async def enoch_resume(resumed_by: str = "mcp", maintenance_mode: bool = False) -> Any:
        """Resume the Enoch queue."""
        return await call_tool(
            mutating.enoch_resume, resumed_by=resumed_by, maintenance_mode=maintenance_mode
        )

    @mcp.tool(
        annotations=mutating_annotations("Enoch Preflight", destructive=False, idempotent=True),
        meta={"userApproval": "required"},
    )
    async def enoch_preflight(payload: dict[str, Any] | None = None) -> Any:
        """Run worker health preflight."""
        return await call_tool(mutating.enoch_preflight, payload=payload)

    @mcp.tool(
        annotations=mutating_annotations("Enoch Intake Notion", destructive=False),
        meta={"userApproval": "required"},
    )
    async def enoch_intake_notion(
        ideas: list[dict[str, Any]],
        idempotency_key: str | None = None,
        source: str = "mcp",
        dry_run: bool = True,
    ) -> Any:
        """Ingest Notion ideas. Defaults to dry_run=True."""
        return await call_tool(
            mutating.enoch_intake_notion,
            ideas=ideas,
            idempotency_key=idempotency_key,
            source=source,
            dry_run=dry_run,
        )

    @mcp.tool(
        annotations=mutating_annotations("Enoch Review Claim", destructive=False),
        meta={"userApproval": "required"},
    )
    async def enoch_review_claim(paper_id: str, claimed_by: str) -> Any:
        """Claim a paper review."""
        return await call_tool(mutating.enoch_review_claim, paper_id, claimed_by)

    @mcp.tool(
        annotations=mutating_annotations("Enoch Review Checklist", destructive=False),
        meta={"userApproval": "required"},
    )
    async def enoch_review_checklist(
        paper_id: str,
        item_id: str,
        status: mutating.ChecklistStatus,
        note: str | None = None,
    ) -> Any:
        """Update a review checklist item."""
        return await call_tool(
            mutating.enoch_review_checklist, paper_id, item_id, status, note=note
        )

    @mcp.tool(
        annotations=mutating_annotations("Enoch Review Status", destructive=False),
        meta={"userApproval": "required"},
    )
    async def enoch_review_status(
        paper_id: str, review_status: str, updated_by: str = "mcp"
    ) -> Any:
        """Update review status."""
        return await call_tool(
            mutating.enoch_review_status, paper_id, review_status, updated_by=updated_by
        )

    @mcp.tool(
        annotations=mutating_annotations("Enoch Draft Paper", destructive=False),
        meta={"userApproval": "required"},
    )
    async def enoch_draft_paper(requested_by: str, force: bool = False) -> Any:
        """Draft the next eligible paper."""
        return await call_tool(mutating.enoch_draft_paper, requested_by, force=force)

    @mcp.tool(
        annotations=mutating_annotations("Enoch Rewrite Draft", destructive=False),
        meta={"userApproval": "required"},
    )
    async def enoch_rewrite_draft(paper_id: str, requested_by: str, force: bool = False) -> Any:
        """Rewrite a paper draft through Enoch's API."""
        return await call_tool(mutating.enoch_rewrite_draft, paper_id, requested_by, force=force)

    return mcp


def run(config: EnochMCPConfig) -> None:
    """Run the server on stdio."""
    create_server(config).run(transport="stdio")
