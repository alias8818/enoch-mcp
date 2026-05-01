from __future__ import annotations

import httpx
import pytest

from enoch_mcp.client import EnochAPIError, EnochClient
from enoch_mcp.config import EnochMCPConfig, load_config


@pytest.mark.asyncio
async def test_client_adds_bearer_auth_and_params() -> None:
    seen = {}

    async def handler(request: httpx.Request) -> httpx.Response:
        seen["auth"] = request.headers.get("authorization")
        seen["url"] = str(request.url)
        return httpx.Response(200, json={"ok": True})

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(base_url="http://enoch.test", transport=transport) as http:
        client = EnochClient(EnochMCPConfig(api_url="http://enoch.test", api_token="test"), http)
        assert await client.get("/control/api/status", {"refresh_worker": True}) == {"ok": True}

    assert seen["auth"] == "Bearer test"
    assert seen["url"] == "http://enoch.test/control/api/status?refresh_worker=true"


@pytest.mark.asyncio
async def test_client_post_json_body() -> None:
    seen = {}

    async def handler(request: httpx.Request) -> httpx.Response:
        seen["body"] = request.content
        return httpx.Response(200, json={"ok": True})

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(base_url="http://enoch.test", transport=transport) as http:
        client = EnochClient(EnochMCPConfig(api_url="http://enoch.test", api_token="test"), http)
        await client.post("/control/dispatch-next", {"dry_run": True, "skip": None})

    assert seen["body"] == b'{"dry_run":true}'


@pytest.mark.asyncio
async def test_client_http_error_message() -> None:
    transport = httpx.MockTransport(lambda _request: httpx.Response(403, text="forbidden"))
    async with httpx.AsyncClient(base_url="http://enoch.test", transport=transport) as http:
        client = EnochClient(EnochMCPConfig(api_url="http://enoch.test", api_token="test"), http)
        with pytest.raises(EnochAPIError, match="HTTP 403: forbidden"):
            await client.get("/control/api/status")


@pytest.mark.asyncio
async def test_client_transport_error_message() -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("boom")

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(base_url="http://enoch.test", transport=transport) as http:
        client = EnochClient(EnochMCPConfig(api_url="http://enoch.test", api_token="test"), http)
        with pytest.raises(EnochAPIError, match="transport error"):
            await client.get("/control/api/status")


@pytest.mark.asyncio
async def test_client_requires_token() -> None:
    transport = httpx.MockTransport(lambda _request: httpx.Response(200, json={}))
    async with httpx.AsyncClient(base_url="http://enoch.test", transport=transport) as http:
        client = EnochClient(EnochMCPConfig(api_url="http://enoch.test"), http)
        with pytest.raises(EnochAPIError, match="Missing Enoch API token"):
            await client.get("/control/api/status")


def test_config_env_and_cli(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENOCH_API_URL", "http://env.test")
    monkeypatch.setenv("ENOCH_API_TOKEN", "env-token")
    assert load_config([]).api_url == "http://env.test"
    assert load_config([]).api_token == "env-token"
    config = load_config(["--api-url", "http://cli.test", "--api-token", "cli-token"])
    assert config.api_url == "http://cli.test"
    assert config.api_token == "cli-token"
