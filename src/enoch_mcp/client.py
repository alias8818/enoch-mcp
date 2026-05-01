"""Async HTTP client for the Enoch API."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import httpx

from .config import EnochMCPConfig

JsonMapping = Mapping[str, Any]


class EnochAPIError(RuntimeError):
    """Raised when Enoch's HTTP API cannot complete a request."""


class EnochClient:
    """Thin async proxy client for Enoch's FastAPI service."""

    def __init__(
        self, config: EnochMCPConfig, http_client: httpx.AsyncClient | None = None
    ) -> None:
        self.config = config
        self._owns_client = http_client is None
        self._client = http_client or httpx.AsyncClient(
            base_url=config.normalized_api_url, timeout=30.0
        )

    async def __aenter__(self) -> EnochClient:
        return self

    async def __aexit__(self, *exc_info: object) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    def _headers(self) -> dict[str, str]:
        if not self.config.api_token:
            raise EnochAPIError("Missing Enoch API token. Set ENOCH_API_TOKEN or pass --api-token.")
        return {"Authorization": f"Bearer {self.config.api_token}"}

    async def get(self, path: str, params: JsonMapping | None = None) -> Any:
        return await self.request("GET", path, params=params)

    async def post(self, path: str, json: JsonMapping | None = None) -> Any:
        return await self.request("POST", path, json=json)

    async def request(
        self,
        method: str,
        path: str,
        *,
        params: JsonMapping | None = None,
        json: JsonMapping | None = None,
    ) -> Any:
        try:
            response = await self._client.request(
                method,
                path,
                params=_clean(params),
                json=_clean(json) if json is not None else None,
                headers=self._headers(),
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            body = exc.response.text.strip()
            detail = f": {body}" if body else ""
            raise EnochAPIError(
                f"Enoch API {method} {path} failed with HTTP {exc.response.status_code}{detail}"
            ) from exc
        except httpx.HTTPError as exc:
            raise EnochAPIError(f"Enoch API {method} {path} transport error: {exc}") from exc

        content_type = response.headers.get("content-type", "")
        if "application/json" in content_type.lower():
            return response.json()
        text = response.text
        return {"content": text} if text else {}


def _clean(values: JsonMapping | None) -> dict[str, Any] | None:
    if values is None:
        return None
    return {key: value for key, value in values.items() if value is not None}
