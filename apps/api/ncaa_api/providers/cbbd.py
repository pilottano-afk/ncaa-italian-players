"""Small authenticated HTTP client for CollegeBasketballData.com.

Endpoint paths are deliberately supplied by callers from the current API reference.
This avoids baking undocumented route names or response assumptions into the app.
"""
import os
from typing import Any
from urllib.parse import urljoin

import httpx


class ProviderNotConfigured(RuntimeError):
    pass


class CollegeBasketballDataClient:
    BASE_URL = "https://api.collegebasketballdata.com/"

    def __init__(self, api_key: str | None = None, timeout: float = 20.0) -> None:
        self.api_key = api_key if api_key is not None else os.getenv("COLLEGEBASKETBALLDATA_API_KEY", "")
        self.timeout = timeout

    @property
    def configured(self) -> bool:
        return bool(self.api_key.strip())

    def get(self, endpoint: str, params: dict[str, Any] | None = None) -> Any:
        if not self.configured:
            raise ProviderNotConfigured(
                "COLLEGEBASKETBALLDATA_API_KEY is not configured. "
                "No request was sent."
            )
        if not endpoint or endpoint.startswith(("http://", "https://")):
            raise ValueError("endpoint must be a relative API path")
        query = dict(params or {})
        # Never allow a caller to accidentally query/import a historical season.
        if "season" in query and int(query["season"]) != 2027:
            raise ValueError("Only season=2027 (NCAA 2026-27) is allowed.")
        query["season"] = 2027
        response = httpx.get(
            urljoin(self.BASE_URL, endpoint.lstrip("/")),
            params=query,
            headers={"Authorization": f"Bearer {self.api_key}", "Accept": "application/json"},
            timeout=self.timeout,
        )
        response.raise_for_status()
        return response.json()
