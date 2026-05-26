from __future__ import annotations

import pytest

from enoch_mcp.config import EnochMCPConfig
from enoch_mcp.server import create_server


@pytest.mark.asyncio
async def test_server_registers_41_tools_with_annotations() -> None:
    server = create_server(EnochMCPConfig(api_token="test"))
    tools = await server.list_tools()
    by_name = {tool.name: tool for tool in tools}

    assert len(tools) == 41
    assert by_name["enoch_status"].annotations.readOnlyHint is True
    assert by_name["enoch_automation_readiness"].annotations.readOnlyHint is True
    assert by_name["enoch_run_detail"].annotations.readOnlyHint is True
    assert by_name["enoch_probe_worker"].annotations.readOnlyHint is True
    assert by_name["enoch_worker_logs"].annotations.readOnlyHint is True
    assert by_name["enoch_worker_artifacts"].annotations.readOnlyHint is True
    assert by_name["enoch_status"].annotations.destructiveHint is False
    assert by_name["enoch_dispatch"].annotations.readOnlyHint is False
    assert by_name["enoch_queue_alert_check"].annotations.readOnlyHint is False
    assert by_name["enoch_dispatch"].annotations.openWorldHint is True
    assert by_name["enoch_pause"].annotations.destructiveHint is True
    assert by_name["enoch_pause"].meta == {"userApproval": "required"}
    assert by_name["enoch_reconcile_stale_lane"].meta == {"userApproval": "required"}
    assert by_name["enoch_draft_paper"].meta == {"userApproval": "required"}
