import logging
import os
from collections.abc import Callable
from typing import Any

from fastapi import HTTPException, Request, status

from app.core.cache import REDIS_EXCEPTIONS, get_redis_client
from app.core.security import decode_access_token

logger = logging.getLogger(__name__)

RATE_LIMIT_ENABLED = os.getenv("RATE_LIMIT_ENABLED", "true").lower() == "true"
DEFAULT_RATE_LIMIT_WINDOW_SECONDS = 60


def _route_key(request: Request) -> str:
    route = request.scope.get("route")
    path = getattr(route, "path", request.url.path)
    return f"{request.method}:{path}"


def _client_identifier(request: Request) -> str:
    authorization = request.headers.get("authorization")
    if authorization and authorization.lower().startswith("bearer "):
        token = authorization.split(" ", 1)[1]
        try:
            payload = decode_access_token(token)
            subject = payload.get("sub")
            if subject:
                return f"account:{subject}"
        except Exception:
            logger.info("Rate limit falling back to IP because bearer token is invalid")

    client_host = request.client.host if request.client else "unknown"
    return f"ip:{client_host}"


def _rate_limit_key(request: Request) -> str:
    return f"rate_limit:{_client_identifier(request)}:{_route_key(request)}"


def _to_int(value: Any, default: int = 0) -> int:
    if isinstance(value, int):
        return value

    if isinstance(value, str) and value.isdigit():
        return int(value)

    logger.warning("Unexpected Redis numeric value type: %s", type(value))
    return default


def rate_limit(
    limit: int,
    window_seconds: int = DEFAULT_RATE_LIMIT_WINDOW_SECONDS,
) -> Callable[[Request], None]:
    def dependency(request: Request) -> None:
        if not RATE_LIMIT_ENABLED:
            logger.info("Rate limit disabled")
            return

        client = get_redis_client()
        if client is None:
            logger.warning("Rate limit skipped because Redis is unavailable")
            return

        key = _rate_limit_key(request)

        try:
            current_count = _to_int(client.incr(key))
            if current_count == 1:
                client.expire(key, window_seconds)

            ttl = _to_int(client.ttl(key), default=window_seconds)
        except REDIS_EXCEPTIONS as exc:
            logger.warning("Rate limit skipped for key %s: %s", key, exc)
            return

        logger.info("Rate limit key=%s count=%s limit=%s ttl=%s", key, current_count, limit, ttl)

        if current_count > limit:
            retry_after = ttl if ttl > 0 else window_seconds
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded.",
                headers={"Retry-After": str(retry_after)},
            )

    return dependency
