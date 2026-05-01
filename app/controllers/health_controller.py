from fastapi import APIRouter, status
from sqlalchemy import text

from app.core.cache import REDIS_EXCEPTIONS, REDIS_URL, get_redis_client
from app.core.database import SessionLocal

router = APIRouter(tags=["Health"])


def _database_status() -> str:
    try:
        with SessionLocal() as db:
            db.execute(text("SELECT 1"))
        return "ok"
    except Exception:
        return "unavailable"


def _redis_status() -> str:
    if not REDIS_URL:
        return "disabled"

    client = get_redis_client()
    if client is None:
        return "unavailable"

    try:
        client.ping()
        return "ok"
    except REDIS_EXCEPTIONS:
        return "unavailable"


@router.get("/health", status_code=status.HTTP_200_OK)
def health_check() -> dict[str, str]:
    database_status = _database_status()
    redis_status = _redis_status()
    service_status = "ok" if database_status == "ok" else "degraded"

    return {
        "status": service_status,
        "database": database_status,
        "redis": redis_status,
    }
