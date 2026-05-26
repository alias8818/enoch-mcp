from __future__ import annotations

import pytest

from enoch_mcp import tools_mutating as tools


class FakeClient:
    def __init__(self) -> None:
        self.calls = []

    async def post(self, path, json=None):
        self.calls.append((path, json))
        return {"path": path, "json": json}


@pytest.mark.asyncio
async def test_mutating_endpoint_mapping_and_safe_defaults() -> None:
    client = FakeClient()
    await tools.enoch_dispatch(client, requested_by="me")
    await tools.enoch_dispatch_one(client, project_id="project-1", requested_by="me")
    await tools.enoch_queue_alert_check(client, requested_by="me")
    await tools.enoch_reconcile_stale_lane(client, requested_by="me", lane_key="cpu_worker")
    await tools.enoch_research_run_cycle(client, requested_by="me")
    await tools.enoch_launch_followup(client, project_id="project-1")
    await tools.enoch_pause(client, reason="maintenance")
    await tools.enoch_resume(client)
    await tools.enoch_preflight(client)
    await tools.enoch_intake_notion(client, ideas=[{"title": "x"}])
    await tools.enoch_intake_ideas(client, ideas=[{"title": "x"}])
    await tools.enoch_review_claim(client, "p1", "me")
    await tools.enoch_review_checklist(client, "p1", "i1", "pass", note="ok")
    await tools.enoch_review_status(client, "p1", "approved")
    await tools.enoch_draft_paper(client, "me")
    await tools.enoch_rewrite_draft(client, "p1", "me")

    paths = [path for path, _json in client.calls]
    assert paths == [
        "/control/dispatch-next",
        "/control/dispatch-one",
        "/control/api/alerts/queue-check",
        "/control/api/alerts/queue-check",
        "/control/api/research/run-cycle",
        "/control/api/v1/followups/launch-next",
        "/control/pause",
        "/control/resume",
        "/control/worker/preflight",
        "/control/intake/notion-ideas",
        "/control/intake/ideas",
        "/control/api/paper-reviews/p1/claim",
        "/control/api/paper-reviews/p1/checklist/i1",
        "/control/api/paper-reviews/p1/status",
        "/control/papers/draft-next",
        "/control/api/paper-reviews/p1/rewrite-draft",
    ]
    assert client.calls[0][1]["dry_run"] is True
    assert client.calls[1][1]["dry_run"] is True
    assert client.calls[2][1]["dry_run"] is True
    assert client.calls[3][1]["dry_run"] is True
    assert client.calls[3][1]["lane_key"] == "cpu_worker"
    assert client.calls[4][1]["dry_run"] is True
    assert client.calls[5][1]["dry_run"] is True
    assert client.calls[8][1] == {}
    assert client.calls[9][1]["dry_run"] is True
    assert client.calls[10][1]["dry_run"] is True
    assert client.calls[14][1]["dry_run"] is True
