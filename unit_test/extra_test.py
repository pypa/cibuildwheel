from __future__ import annotations

import time
import urllib.error
import urllib.request
from email.message import Message
from typing import Any

from cibuildwheel import extra

TYPE_CHECKING = False
if TYPE_CHECKING:
    import pytest


def test_github_api_request_waits_for_rate_limit_reset(monkeypatch: pytest.MonkeyPatch) -> None:
    headers = Message()
    headers["x-ratelimit-remaining"] = "0"
    headers["x-ratelimit-reset"] = str(int(time.time()) + 42)
    headers["date"] = "Wed, 23 Sep 2026 16:01:43 GMT"
    error = urllib.error.HTTPError(
        "https://api.github.com", 403, "rate limit exceeded", headers, None
    )
    urls: list[str] = []
    sleeps: list[float] = []

    def fake_json_request(request: urllib.request.Request) -> dict[str, Any]:
        urls.append(request.full_url)
        if len(urls) == 1:
            raise error
        return {"tag_name": "v1"}

    monkeypatch.setattr(extra, "_json_request", fake_json_request)
    monkeypatch.setattr(time, "sleep", sleeps.append)

    assert extra.github_api_request("repos/pypa/cibuildwheel/releases/latest") == {"tag_name": "v1"}
    assert urls == ["https://api.github.com/repos/pypa/cibuildwheel/releases/latest"] * 2
    assert 40 <= sleeps[0] <= 42
    error.close()


def test_github_api_request_uses_github_token(monkeypatch: pytest.MonkeyPatch) -> None:
    requests: list[urllib.request.Request] = []

    def fake_json_request(request: urllib.request.Request) -> dict[str, Any]:
        requests.append(request)
        return {}

    monkeypatch.setattr(extra, "_json_request", fake_json_request)

    monkeypatch.setenv("GITHUB_TOKEN", "secret")
    extra.github_api_request("repos/pypa/cibuildwheel/releases/latest")
    assert requests[-1].get_header("Authorization") == "Bearer secret"

    monkeypatch.delenv("GITHUB_TOKEN")
    extra.github_api_request("repos/pypa/cibuildwheel/releases/latest")
    assert not requests[-1].has_header("Authorization")
