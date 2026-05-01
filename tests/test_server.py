from __future__ import annotations

import pytest

from enoch_mcp.config import EnochMCPConfig
from enoch_mcp.server import create_server


@pytest.mark.asyncio
async def test_server_registers_22_tools_with_annotations() -> None:
    server = create_server(EnochMCPConfig(api_token="test"))
    tools = await server.list_tools()
    by_name = {tool.name: tool for tool in tools}

    assert len(tools) == 22
    assert by_name["enoch_status"].annotations.readOnlyHint is True
    assert by_name["enoch_status"].annotations.destructiveHint is False
    assert by_name["enoch_dispatch"].annotations.readOnlyHint is False
    assert by_name["enoch_dispatch"].annotations.openWorldHint is True
    assert by_name["enoch_pause"].annotations.destructiveHint is True
    assert by_name["enoch_pause"].meta == {"userApproval": "required"}
