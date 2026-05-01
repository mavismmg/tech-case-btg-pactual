import json
import logging
import os
from contextlib import contextmanager
from typing import Any, Iterator

try:
    import redis
    from redis.exceptions import RedisError as RedisClientError

    REDIS_EXCEPTIONS: tuple[type[BaseException], ...] = (RedisClientError,)
except ImportError:
    redis = None
    REDIS_EXCEPTIONS = (Exception,)


logger = logging.getLogger(__name__)

REDIS_URL = os.getenv("REDIS_URL")
DEFAULT_CACHE_TTL_SECONDS = 60
DEFAULT_LOCK_TIMEOUT_SECONDS = 10
DEFAULT_LOCK_BLOCKING_TIMEOUT_SECONDS = 3

_redis_client = None


def get_redis_client():
    global _redis_client

    if not REDIS_URL:
        logger.info("Redis cache disabled: REDIS_URL is not set")
        return None

    if redis is None:
        logger.info("Redis cache disabled: redis package is not installed")
        return None

    if _redis_client is None:
        try:
            _redis_client = redis.Redis.from_url(
                REDIS_URL,
                decode_responses=True,
                socket_connect_timeout=1,
                socket_timeout=1,
            )
            _redis_client.ping()
            logger.info("Redis cache connected: %s", REDIS_URL)
        except REDIS_EXCEPTIONS as exc:
            logger.warning("Redis cache unavailable: %s", exc)
            _redis_client = None

    return _redis_client


def get_json(key: str) -> Any | None:
    client = get_redis_client()
    if client is None:
        logger.info("Redis cache skipped for key %s", key)
        return None

    try:
        value = client.get(key)
        if value is None:
            logger.info("Redis cache miss: %s", key)
            return None

        if not isinstance(value, (str, bytes, bytearray)):
            logger.warning("Unexpected cache value type for key %s: %s", key, type(value))
            return None

        logger.info("Redis cache hit: %s", key)
        return json.loads(value)
    except (*REDIS_EXCEPTIONS, json.JSONDecodeError) as exc:
        logger.warning("Failed to read cache key %s: %s", key, exc)
        return None


def set_json(key: str, value: Any, ttl_seconds: int = DEFAULT_CACHE_TTL_SECONDS) -> None:
    client = get_redis_client()
    if client is None:
        logger.info("Redis cache write skipped for key %s", key)
        return

    try:
        client.setex(key, ttl_seconds, json.dumps(value, default=str))
        logger.info("Redis cache set: %s ttl=%ss", key, ttl_seconds)
    except (*REDIS_EXCEPTIONS, TypeError) as exc:
        logger.warning("Failed to write cache key %s: %s", key, exc)


def delete_keys(*keys: str) -> None:
    client = get_redis_client()
    if client is None or not keys:
        if keys:
            logger.info("Redis cache invalidation skipped for keys %s", keys)
        return

    try:
        deleted_count = client.delete(*keys)
        logger.info("Redis cache invalidated keys=%s deleted=%s", keys, deleted_count)
    except REDIS_EXCEPTIONS as exc:
        logger.warning("Failed to delete cache keys %s: %s", keys, exc)


def delete_by_prefix(prefix: str) -> None:
    client = get_redis_client()
    if client is None:
        logger.info("Redis cache prefix invalidation skipped for prefix %s", prefix)
        return

    try:
        pattern = f"{prefix}*"
        keys = list(client.scan_iter(match=pattern))
        if not keys:
            logger.info("Redis cache prefix invalidation found no keys for prefix %s", prefix)
            return

        deleted_count = client.delete(*keys)
        logger.info("Redis cache invalidated prefix=%s deleted=%s", prefix, deleted_count)
    except REDIS_EXCEPTIONS as exc:
        logger.warning("Failed to delete cache keys with prefix %s: %s", prefix, exc)


@contextmanager
def redis_lock(
    key: str,
    timeout_seconds: int = DEFAULT_LOCK_TIMEOUT_SECONDS,
    blocking_timeout_seconds: int = DEFAULT_LOCK_BLOCKING_TIMEOUT_SECONDS,
) -> Iterator[bool]:
    client = get_redis_client()
    if client is None:
        logger.info("Redis lock skipped: %s", key)
        yield False
        return

    lock = client.lock(
        key,
        timeout=timeout_seconds,
        blocking_timeout=blocking_timeout_seconds,
    )

    acquired = False
    try:
        acquired = lock.acquire()
        if acquired:
            logger.info("Redis lock acquired: %s", key)
        else:
            logger.warning("Redis lock not acquired before timeout: %s", key)
        yield acquired
    except REDIS_EXCEPTIONS as exc:
        logger.warning("Redis lock %s unavailable: %s", key, exc)
        yield False
    finally:
        if acquired:
            try:
                lock.release()
                logger.info("Redis lock released: %s", key)
            except REDIS_EXCEPTIONS as exc:
                logger.warning("Failed to release Redis lock %s: %s", key, exc)
