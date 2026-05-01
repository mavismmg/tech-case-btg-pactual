from contextlib import contextmanager
from datetime import datetime, timedelta, timezone

from app.models.loan_due_notification import LoanDueNotification
from app.schemas.notification import NotificationChannel
from app.services import notification_scheduler, notification_service


def test_due_loan_selection_includes_only_active_loans_inside_window(
    db,
    loan_factory,
    returned_loan_factory,
    overdue_loan_factory,
):
    now = datetime(2026, 5, 1, 10, 0, tzinfo=timezone.utc)
    due_loan = loan_factory(expected_return_date=now + timedelta(hours=8))
    outside_window_loan = loan_factory(expected_return_date=now + timedelta(days=3))
    returned_loan_factory(expected_return_date=now + timedelta(hours=10))
    overdue_loan_factory(days_overdue=1)

    items = notification_service.list_due_loan_notification_items(db, days_ahead=1, now=now)

    assert [item.loan_id for item in items] == [due_loan.id]
    assert outside_window_loan.id not in [item.loan_id for item in items]


def test_fake_email_delivery_is_recorded_and_returned(db, loan_factory):
    now = datetime(2026, 5, 1, 10, 0, tzinfo=timezone.utc)
    loan = loan_factory(expected_return_date=now + timedelta(days=1))

    response = notification_service.send_due_loan_notifications(
        db,
        days_ahead=1,
        channel=NotificationChannel.EMAIL,
        now=now,
    )

    assert response.total_due_loans == 1
    assert response.sent_email_count == 1
    assert response.sent_webhook_count == 0
    assert response.failed_count == 0
    assert response.deliveries[0].loan_id == loan.id
    assert response.deliveries[0].channel == "email"
    assert response.deliveries[0].to == loan.user.email
    assert "Vencimento de empréstimo" in response.deliveries[0].subject


def test_webhook_delivery_posts_batch_payload(db, loan_factory, monkeypatch):
    now = datetime(2026, 5, 1, 10, 0, tzinfo=timezone.utc)
    loan = loan_factory(expected_return_date=now + timedelta(days=1))
    calls = []

    class FakeResponse:
        def raise_for_status(self):
            return None

    def fake_post(url, json, timeout):
        calls.append({"url": url, "json": json, "timeout": timeout})
        return FakeResponse()

    monkeypatch.setattr(notification_service.httpx, "post", fake_post)

    response = notification_service.send_due_loan_notifications(
        db,
        days_ahead=1,
        channel=NotificationChannel.WEBHOOK,
        now=now,
        webhook_url="https://example.com/due-loans",
    )

    assert response.sent_webhook_count == 1
    assert response.failed_count == 0
    assert calls[0]["url"] == "https://example.com/due-loans"
    assert calls[0]["json"]["event"] == "due_loans_notification"
    assert calls[0]["json"]["loans"][0]["loan_id"] == loan.id


def test_webhook_without_url_records_controlled_failure(db, loan_factory, monkeypatch):
    now = datetime(2026, 5, 1, 10, 0, tzinfo=timezone.utc)
    loan = loan_factory(expected_return_date=now + timedelta(days=1))
    monkeypatch.delenv("DUE_LOAN_WEBHOOK_URL", raising=False)

    response = notification_service.send_due_loan_notifications(
        db,
        days_ahead=1,
        channel=NotificationChannel.WEBHOOK,
        now=now,
    )

    assert response.total_due_loans == 1
    assert response.sent_webhook_count == 0
    assert response.failed_count == 1
    assert response.deliveries[0].loan_id == loan.id
    assert response.deliveries[0].status == "failed"
    assert response.deliveries[0].error_message == "DUE_LOAN_WEBHOOK_URL is not configured."


def test_notification_idempotency_skips_repeated_channel_for_same_day(db, loan_factory):
    now = datetime(2026, 5, 1, 10, 0, tzinfo=timezone.utc)
    loan_factory(expected_return_date=now + timedelta(hours=2))

    first_response = notification_service.send_due_loan_notifications(
        db,
        days_ahead=1,
        channel=NotificationChannel.EMAIL,
        now=now,
    )
    second_response = notification_service.send_due_loan_notifications(
        db,
        days_ahead=1,
        channel=NotificationChannel.EMAIL,
        now=now,
    )

    assert first_response.sent_email_count == 1
    assert second_response.sent_email_count == 0
    assert second_response.skipped_count == 1
    assert db.query(LoanDueNotification).count() == 1


def test_webhook_idempotency_does_not_post_duplicate_batch(db, loan_factory, monkeypatch):
    now = datetime(2026, 5, 1, 10, 0, tzinfo=timezone.utc)
    loan_factory(expected_return_date=now + timedelta(hours=2))
    calls = []

    class FakeResponse:
        def raise_for_status(self):
            return None

    def fake_post(url, json, timeout):
        calls.append(json)
        return FakeResponse()

    monkeypatch.setattr(notification_service.httpx, "post", fake_post)

    first_response = notification_service.send_due_loan_notifications(
        db,
        days_ahead=1,
        channel=NotificationChannel.WEBHOOK,
        now=now,
        webhook_url="https://example.com/due-loans",
    )
    second_response = notification_service.send_due_loan_notifications(
        db,
        days_ahead=1,
        channel=NotificationChannel.WEBHOOK,
        now=now,
        webhook_url="https://example.com/due-loans",
    )

    assert first_response.sent_webhook_count == 1
    assert second_response.sent_webhook_count == 0
    assert second_response.skipped_count == 1
    assert len(calls) == 1


def test_scheduler_does_not_run_when_disabled(monkeypatch):
    calls = []
    scheduler = notification_scheduler.DueLoanNotificationScheduler(enabled=False)

    monkeypatch.setattr(scheduler, "run_once", lambda: calls.append("run"))
    scheduler.start()

    assert calls == []
    assert scheduler._thread is None


def test_scheduler_run_once_uses_redis_lock(monkeypatch):
    calls = []

    @contextmanager
    def fake_lock(*args, **kwargs):
        calls.append({"args": args, "kwargs": kwargs})
        yield False

    monkeypatch.setattr(notification_scheduler, "redis_lock", fake_lock)

    scheduler = notification_scheduler.DueLoanNotificationScheduler(enabled=True)
    scheduler.run_once()

    assert calls[0]["args"][0] == notification_scheduler.SCHEDULER_LOCK_KEY
