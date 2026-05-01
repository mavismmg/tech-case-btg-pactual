import logging
import os
import threading
from datetime import timezone, datetime

from app.core.cache import redis_lock
from app.core.database import SessionLocal
from app.schemas.notification import NotificationChannel
from app.services import notification_service

logger = logging.getLogger(__name__)

SCHEDULER_LOCK_KEY = "notifications:due-loans:scheduler"


def _env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.lower() in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        logger.warning("Invalid integer env var %s=%s; using default %s", name, value, default)
        return default


class DueLoanNotificationScheduler:
    def __init__(
        self,
        *,
        enabled: bool | None = None,
        interval_seconds: int | None = None,
        days_ahead: int | None = None,
    ) -> None:
        self.enabled = _env_bool("DUE_LOAN_NOTIFICATIONS_ENABLED") if enabled is None else enabled
        self.interval_seconds = max(
            60,
            interval_seconds
            if interval_seconds is not None
            else _env_int("DUE_LOAN_NOTIFICATION_INTERVAL_SECONDS", 3600),
        )
        self.days_ahead = max(
            0,
            days_ahead if days_ahead is not None else _env_int("DUE_LOAN_NOTIFICATION_DAYS_AHEAD", 1),
        )
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if not self.enabled:
            logger.info("Due loan notification scheduler disabled")
            return

        if self._thread is not None and self._thread.is_alive():
            return

        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, name="due-loan-notification-scheduler", daemon=True)
        self._thread.start()
        logger.info(
            "Due loan notification scheduler started",
            extra={"interval_seconds": self.interval_seconds, "days_ahead": self.days_ahead},
        )

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=5)
            self._thread = None
        logger.info("Due loan notification scheduler stopped")

    def run_once(self) -> None:
        with redis_lock(
            SCHEDULER_LOCK_KEY,
            timeout_seconds=max(self.interval_seconds, 60),
            blocking_timeout_seconds=0,
        ) as acquired:
            if not acquired:
                logger.info("Due loan notification scheduler skipped because lock was not acquired")
                return

            db = SessionLocal()
            try:
                notification_service.send_due_loan_notifications(
                    db,
                    days_ahead=self.days_ahead,
                    channel=NotificationChannel.ALL,
                    now=datetime.now(timezone.utc),
                )
            finally:
                db.close()

    def _run(self) -> None:
        while not self._stop_event.is_set():
            try:
                self.run_once()
            except Exception:
                logger.exception("Due loan notification scheduler iteration failed")

            self._stop_event.wait(self.interval_seconds)
