from __future__ import annotations

import pytest

from enoch_mcp import tools_readonly as tools


class FakeClient:
    def __init__(self) -> None:
        self.calls = []

    async def get(self, path, params=None):
        self.calls.append((path, params))
        return {"path": path, "params": params}


@pytest.mark.asyncio
async def test_readonly_endpoint_mapping() -> None:
    client = FakeClient()
    await tools.enoch_status(client)
    await tools.enoch_queue_health(client)
    await tools.enoch_queue_list(client, "queued", search="gpu")
    await tools.enoch_papers_list(client, status="publication_draft")
    await tools.enoch_paper_detail(client, "p1")
    await tools.enoch_paper_artifact(client, "p1", "manifest_path")
    await tools.enoch_reviews_list(client, review_status="open")
    await tools.enoch_review_next(client)
    await tools.enoch_events(client, entity_type="paper")
    await tools.enoch_core_health(client)
    await tools.enoch_core_queue_projection(client, mode="shadow")
    await tools.enoch_core_paper_candidates(client, "polish", mode="compare")

    paths = [path for path, _params in client.calls]
    assert paths == [
        "/control/api/status",
        "/control/api/queue-health",
        "/control/api/queues/queued",
        "/control/api/papers",
        "/control/api/papers/p1",
        "/control/api/papers/p1/artifact/manifest_path",
        "/control/api/paper-reviews",
        "/control/api/paper-reviews/next",
        "/control/api/events",
        "/enoch-core/health",
        "/enoch-core/projections/queue",
        "/enoch-core/candidates/paper-polish",
    ]
    assert client.calls[0][1] == {"refresh_worker": True}
    assert client.calls[2][1] == {"page_size": 100, "search": "gpu"}
    assert client.calls[11][1] == {"mode": "compare"}
