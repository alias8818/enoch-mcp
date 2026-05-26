from __future__ import annotations

import pytest

from enoch_mcp import tools_readonly as tools
from enoch_mcp.config import EnochMCPConfig, WorkerProbeTarget


class FakeClient:
    def __init__(self) -> None:
        self.calls = []
        self.config = EnochMCPConfig(api_token="test")

    async def get(self, path, params=None):
        self.calls.append((path, params))
        return {"path": path, "params": params}


@pytest.mark.asyncio
async def test_readonly_endpoint_mapping() -> None:
    client = FakeClient()
    await tools.enoch_status(client)
    await tools.enoch_queue_health(client)
    await tools.enoch_overview(client)
    await tools.enoch_automation_readiness(client)
    await tools.enoch_research_quality(client)
    await tools.enoch_intake_status(client)
    await tools.enoch_lanes(client)
    await tools.enoch_probe_worker(client, lane="cpu")
    await tools.enoch_worker_logs(client, lane="cpu")
    await tools.enoch_worker_artifacts(client, lane="cpu", project_id="project-1")
    await tools.enoch_queue_list(client, "queued", search="gpu")
    await tools.enoch_v1_queue(client, queue="active", search="gpu")
    await tools.enoch_projects(client, search="ledger")
    await tools.enoch_project_detail(client, "project-1")
    await tools.enoch_runs(client, state="awaiting_wake")
    await tools.enoch_run_detail(client, "run-1")
    await tools.enoch_papers_list(client, status="publication_draft")
    await tools.enoch_paper_detail(client, "p1")
    await tools.enoch_paper_artifact(client, "p1", "manifest_path")
    await tools.enoch_reviews_list(client, review_status="open")
    await tools.enoch_review_next(client)
    await tools.enoch_events(client, entity_type="paper", include_payload=True)
    await tools.enoch_core_health(client)
    await tools.enoch_core_queue_projection(client, mode="shadow")
    await tools.enoch_core_paper_candidates(client, "polish", mode="compare")

    paths = [path for path, _params in client.calls]
    assert paths == [
        "/control/api/status",
        "/control/api/queue-health",
        "/control/api/v1/overview",
        "/control/api/v1/automation-readiness",
        "/control/api/v1/research-quality",
        "/control/api/intake/ideas",
        "/control/api/v1/lanes",
        "/control/api/queues/queued",
        "/control/api/v1/queue",
        "/control/api/v1/projects",
        "/control/api/v1/projects/project-1",
        "/control/api/v1/runs",
        "/control/api/v1/runs/run-1",
        "/control/api/papers",
        "/control/api/papers/p1",
        "/control/api/papers/p1/artifact/manifest_path",
        "/control/api/paper-reviews",
        "/control/api/paper-reviews/next",
        "/control/api/v1/events",
        "/enoch-core/health",
        "/enoch-core/projections/queue",
        "/enoch-core/candidates/paper-polish",
    ]
    assert client.calls[0][1] == {"refresh_worker": True}
    assert client.calls[2][1] == {"active_limit": 5, "event_limit": 10}
    assert client.calls[5][1] == {"page_size": 50, "include_latest_payload": False}
    assert client.calls[7][1] == {"page_size": 100, "search": "gpu"}
    assert client.calls[8][1] == {
        "queue": "active",
        "status": "",
        "search": "gpu",
        "cursor": "",
        "page_size": 50,
        "sort": "priority",
    }
    assert client.calls[21][1] == {"mode": "compare"}


@pytest.mark.asyncio
async def test_worker_probe_not_configured_is_explicit() -> None:
    client = FakeClient()
    result = await tools.enoch_probe_worker(client, lane="cpu")
    assert result["ok"] is False
    assert result["reason"] == "no worker probe targets configured"


@pytest.mark.asyncio
async def test_worker_probe_requires_lane_when_multiple_targets() -> None:
    client = FakeClient()
    client.config = EnochMCPConfig(
        api_token="test",
        worker_probe_targets={
            "cpu": WorkerProbeTarget(lane="cpu", api_url="http://cpu.example"),
            "gb10": WorkerProbeTarget(lane="gb10", api_url="http://gb10.example"),
        },
    )
    result = await tools.enoch_probe_worker(client)
    assert result["ok"] is False
    assert result["configured_lanes"] == ["cpu", "gb10"]


@pytest.mark.asyncio
async def test_worker_artifact_rejects_unsafe_project_id() -> None:
    client = FakeClient()
    client.config = EnochMCPConfig(
        api_token="test",
        worker_probe_targets={"cpu": WorkerProbeTarget(lane="cpu", ssh_host="worker")},
    )
    with pytest.raises(ValueError, match="project_id contains unsupported characters"):
        await tools.enoch_worker_artifacts(client, lane="cpu", project_id="../escape")
