import pytest
from fastapi import HTTPException
from starlette.requests import Request
from starlette.types import Scope

import app.core.rate_limit as rate_limit_module


class FakeRedis:
    def __init__(self):
        self.values = {}
        self.ttls = {}

    def incr(self, key):
        self.values[key] = self.values.get(key, 0) + 1
        return self.values[key]

    def expire(self, key, window_seconds):
        self.ttls[key] = window_seconds

    def ttl(self, key):
        return self.ttls.get(key, -1)


def _request(path: str = "/loans/", token: str | None = None) -> Request:
    headers = {}
    if token:
        headers["authorization"] = f"Bearer {token}"

    raw_headers = [
        (name.lower().encode("latin-1"), value.encode("latin-1"))
        for name, value in headers.items()
    ]
    scope: Scope = {
        "type": "http",
        "method": "POST",
        "path": path,
        "headers": raw_headers,
        "client": ("127.0.0.1", 12345),
        "server": ("testserver", 80),
        "scheme": "http",
        "route": type("Route", (), {"path": path})(),
    }
    return Request(scope)


def test_rate_limit_allows_requests_under_limit(monkeypatch):
    fake_redis = FakeRedis()
    monkeypatch.setattr(rate_limit_module, "RATE_LIMIT_ENABLED", True)
    monkeypatch.setattr(rate_limit_module, "get_redis_client", lambda: fake_redis)

    dependency = rate_limit_module.rate_limit(limit=2, window_seconds=60)

    dependency(_request())
    dependency(_request())

    assert next(iter(fake_redis.values.values())) == 2


def test_rate_limit_blocks_requests_above_limit(monkeypatch):
    fake_redis = FakeRedis()
    monkeypatch.setattr(rate_limit_module, "RATE_LIMIT_ENABLED", True)
    monkeypatch.setattr(rate_limit_module, "get_redis_client", lambda: fake_redis)

    dependency = rate_limit_module.rate_limit(limit=1, window_seconds=60)
    dependency(_request())

    with pytest.raises(HTTPException) as exc_info:
        dependency(_request())

    assert exc_info.value.status_code == 429
    assert exc_info.value.headers is not None
    assert exc_info.value.headers["Retry-After"] == "60"


def test_rate_limit_uses_account_identifier_when_token_is_valid(monkeypatch):
    fake_redis = FakeRedis()
    monkeypatch.setattr(rate_limit_module, "RATE_LIMIT_ENABLED", True)
    monkeypatch.setattr(rate_limit_module, "get_redis_client", lambda: fake_redis)
    monkeypatch.setattr(rate_limit_module, "decode_access_token", lambda token: {"sub": "42"})

    dependency = rate_limit_module.rate_limit(limit=2, window_seconds=60)
    dependency(_request(token="valid-token"))

    key = next(iter(fake_redis.values))
    assert "account:42" in key


def test_rate_limit_fails_open_without_redis(monkeypatch):
    monkeypatch.setattr(rate_limit_module, "RATE_LIMIT_ENABLED", True)
    monkeypatch.setattr(rate_limit_module, "get_redis_client", lambda: None)

    dependency = rate_limit_module.rate_limit(limit=1, window_seconds=60)

    dependency(_request())
