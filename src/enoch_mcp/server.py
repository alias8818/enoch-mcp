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

    @mcp.tool(annotations=readonly_annotations("Enoch Overview"))
    async def enoch_overview(active_limit: int = 5, event_limit: int = 10) -> Any:
        """Bounded Dashboard V1 overview: operator counts, lanes, papers, top actions, events."""
        return await call_tool(
            readonly.enoch_overview, active_limit=active_limit, event_limit=event_limit
        )

    @mcp.tool(annotations=readonly_annotations("Enoch Automation Readiness"))
    async def enoch_automation_readiness() -> Any:
        """Canonical long-haul readiness check used to answer whether Enoch can run unattended."""
        return await call_tool(readonly.enoch_automation_readiness)

    @mcp.tool(annotations=readonly_annotations("Enoch Research Quality"))
    async def enoch_research_quality() -> Any:
        """Latest research quality readiness report."""
        return await call_tool(readonly.enoch_research_quality)

    @mcp.tool(annotations=readonly_annotations("Enoch Intake Status"))
    async def enoch_intake_status(
        page_size: int = 50, include_latest_payload: bool = False
    ) -> Any:
        """Current control-plane idea intake status."""
        return await call_tool(
            readonly.enoch_intake_status,
            page_size=page_size,
            include_latest_payload=include_latest_payload,
        )

    @mcp.tool(annotations=readonly_annotations("Enoch Lanes"))
    async def enoch_lanes() -> Any:
        """Bounded worker lane state and lane-aware next candidate."""
        return await call_tool(readonly.enoch_lanes)

    @mcp.tool(annotations=readonly_annotations("Enoch Probe Worker"))
    async def enoch_probe_worker(
        lane: readonly.WorkerLane | None = None,
        run_id: str | None = None,
    ) -> Any:
        """Optional direct worker probe: health, wake-gate status, processes, and disk."""
        return await call_tool(readonly.enoch_probe_worker, lane=lane, run_id=run_id)

    @mcp.tool(annotations=readonly_annotations("Enoch Worker Logs"))
    async def enoch_worker_logs(
        lane: readonly.WorkerLane | None = None,
        log_kind: readonly.WorkerLogKind = "service",
        run_id: str | None = None,
        lines: int = 80,
    ) -> Any:
        """Optional bounded worker log tail from allowlisted log sources."""
        return await call_tool(
            readonly.enoch_worker_logs,
            lane=lane,
            log_kind=log_kind,
            run_id=run_id,
            lines=lines,
        )

    @mcp.tool(annotations=readonly_annotations("Enoch Worker Artifacts"))
    async def enoch_worker_artifacts(
        lane: readonly.WorkerLane | None = None,
        project_id: str | None = None,
        run_id: str | None = None,
    ) -> Any:
        """Optional expected artifact presence check for a worker project/run."""
        return await call_tool(
            readonly.enoch_worker_artifacts,
            lane=lane,
            project_id=project_id,
            run_id=run_id,
        )

    @mcp.tool(annotations=readonly_annotations("Enoch Queue List"))
    async def enoch_queue_list(
        status: readonly.QueueStatus, search: str | None = None, page_size: int = 100
    ) -> Any:
        """List queue items by status: active, queued, blocked, or paused."""
        return await call_tool(
            readonly.enoch_queue_list, status, search=search, page_size=page_size
        )

    @mcp.tool(annotations=readonly_annotations("Enoch V1 Queue"))
    async def enoch_v1_queue(
        queue: readonly.V1Queue = "all",
        status: str = "",
        search: str = "",
        cursor: str = "",
        page_size: int = 50,
        sort: str = "priority",
    ) -> Any:
        """Bounded Dashboard V1 queue list with cursor pagination."""
        return await call_tool(
            readonly.enoch_v1_queue,
            queue=queue,
            status=status,
            search=search,
            cursor=cursor,
            page_size=page_size,
            sort=sort,
        )

    @mcp.tool(annotations=readonly_annotations("Enoch Projects"))
    async def enoch_projects(
        status: str = "",
        search: str = "",
        cursor: str = "",
        page_size: int = 50,
        sort: str = "recent",
    ) -> Any:
        """Bounded Dashboard V1 project list."""
        return await call_tool(
            readonly.enoch_projects,
            status=status,
            search=search,
            cursor=cursor,
            page_size=page_size,
            sort=sort,
        )

    @mcp.tool(annotations=readonly_annotations("Enoch Project Detail"))
    async def enoch_project_detail(project_id: str, event_limit: int = 50) -> Any:
        """Bounded project detail with related queue/run/paper rows and events."""
        return await call_tool(
            readonly.enoch_project_detail, project_id, event_limit=event_limit
        )

    @mcp.tool(annotations=readonly_annotations("Enoch Runs"))
    async def enoch_runs(
        state: str = "",
        project_id: str = "",
        search: str = "",
        cursor: str = "",
        page_size: int = 50,
        sort: str = "recent",
    ) -> Any:
        """Bounded Dashboard V1 run list."""
        return await call_tool(
            readonly.enoch_runs,
            state=state,
            project_id=project_id,
            search=search,
            cursor=cursor,
            page_size=page_size,
            sort=sort,
        )

    @mcp.tool(annotations=readonly_annotations("Enoch Run Detail"))
    async def enoch_run_detail(run_id: str, event_limit: int = 50) -> Any:
        """Bounded run detail with related queue/paper rows and events."""
        return await call_tool(readonly.enoch_run_detail, run_id, event_limit=event_limit)

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
        """Query the bounded Dashboard V1 event log."""
        return await call_tool(
            readonly.enoch_events,
            event_id=event_id,
            entity_type=entity_type,
            entity_id=entity_id,
            event_type=event_type,
            search=search,
            cursor=cursor,
            page_size=page_size,
            include_payload=include_payload,
            sort=sort,
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
        annotations=mutating_annotations("Enoch Dispatch One", destructive=False),
        meta={"userApproval": "required"},
    )
    async def enoch_dispatch_one(
        project_id: str,
        requested_by: str,
        dry_run: bool = True,
        force_preflight: bool = True,
    ) -> Any:
        """Dispatch one explicit queued project. Defaults to dry_run=True."""
        return await call_tool(
            mutating.enoch_dispatch_one,
            project_id,
            requested_by=requested_by,
            dry_run=dry_run,
            force_preflight=force_preflight,
        )

    @mcp.tool(
        annotations=mutating_annotations("Enoch Queue Alert Check", destructive=False),
        meta={"userApproval": "required"},
    )
    async def enoch_queue_alert_check(
        requested_by: str,
        dry_run: bool = True,
        refresh_worker: bool = True,
        force_notify: bool = False,
        lane_key: str | None = None,
        machine_target: str | None = None,
        project_id: str | None = None,
        run_id: str | None = None,
    ) -> Any:
        """Run queue alert/stale-active reconciliation. Defaults to dry_run=True."""
        return await call_tool(
            mutating.enoch_queue_alert_check,
            requested_by=requested_by,
            dry_run=dry_run,
            refresh_worker=refresh_worker,
            force_notify=force_notify,
            lane_key=lane_key,
            machine_target=machine_target,
            project_id=project_id,
            run_id=run_id,
        )

    @mcp.tool(
        annotations=mutating_annotations("Enoch Reconcile Stale Lane", destructive=False),
        meta={"userApproval": "required"},
    )
    async def enoch_reconcile_stale_lane(
        requested_by: str,
        dry_run: bool = True,
        refresh_worker: bool = True,
        lane_key: str | None = None,
        machine_target: str | None = None,
        project_id: str | None = None,
        run_id: str | None = None,
    ) -> Any:
        """Explain or reconcile one stale active lane. Defaults to dry_run=True."""
        return await call_tool(
            mutating.enoch_reconcile_stale_lane,
            requested_by=requested_by,
            dry_run=dry_run,
            refresh_worker=refresh_worker,
            lane_key=lane_key,
            machine_target=machine_target,
            project_id=project_id,
            run_id=run_id,
        )

    @mcp.tool(
        annotations=mutating_annotations("Enoch Research Run Cycle", destructive=False),
        meta={"userApproval": "required"},
    )
    async def enoch_research_run_cycle(
        requested_by: str,
        dry_run: bool = True,
        refresh_worker: bool = True,
    ) -> Any:
        """Run one bounded research autopilot cycle. Defaults to dry_run=True."""
        return await call_tool(
            mutating.enoch_research_run_cycle,
            requested_by=requested_by,
            dry_run=dry_run,
            refresh_worker=refresh_worker,
        )

    @mcp.tool(
        annotations=mutating_annotations("Enoch Launch Follow-up", destructive=False),
        meta={"userApproval": "required"},
    )
    async def enoch_launch_followup(
        project_id: str = "",
        requested_by: str = "mcp",
        dry_run: bool = True,
        max_followup_depth: int = 4,
    ) -> Any:
        """Launch the next bounded follow-up candidate. Defaults to dry_run=True."""
        return await call_tool(
            mutating.enoch_launch_followup,
            project_id=project_id,
            requested_by=requested_by,
            dry_run=dry_run,
            max_followup_depth=max_followup_depth,
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
        annotations=mutating_annotations("Enoch Intake Ideas", destructive=False),
        meta={"userApproval": "required"},
    )
    async def enoch_intake_ideas(
        ideas: list[dict[str, Any]],
        idempotency_key: str | None = None,
        source: str = "mcp",
        dry_run: bool = True,
        default_machine_target: str | None = None,
        default_model: str | None = None,
        default_sandbox: str | None = None,
        include_statuses: list[str] | None = None,
        workload_machine_targets: dict[str, str] | None = None,
        override_existing_dispatch_metadata: bool = False,
    ) -> Any:
        """Ingest ideas through the current control-plane intake API. Defaults to dry_run=True."""
        return await call_tool(
            mutating.enoch_intake_ideas,
            ideas=ideas,
            idempotency_key=idempotency_key,
            source=source,
            dry_run=dry_run,
            default_machine_target=default_machine_target,
            default_model=default_model,
            default_sandbox=default_sandbox,
            include_statuses=include_statuses,
            workload_machine_targets=workload_machine_targets,
            override_existing_dispatch_metadata=override_existing_dispatch_metadata,
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
    async def enoch_draft_paper(
        requested_by: str, dry_run: bool = True, force: bool = False
    ) -> Any:
        """Draft the next eligible paper. Defaults to dry_run=True."""
        return await call_tool(
            mutating.enoch_draft_paper, requested_by, dry_run=dry_run, force=force
        )

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
