import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx
from sqlalchemy.orm import Session

from app.models.loan import Loan
from app.models.loan_due_notification import (
    LoanDueNotificationChannel,
    LoanDueNotificationStatus,
)
from app.repositories import loan_due_notification_repository
from app.schemas.notification import (
    DueLoanNotificationItem,
    DueLoanNotificationResponse,
    NotificationChannel,
    NotificationDeliveryResponse,
)

logger = logging.getLogger(__name__)

WEBHOOK_TIMEOUT_SECONDS = 5.0


def _normalize_datetime(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


def _loan_to_notification_item(loan: Loan, now: datetime) -> DueLoanNotificationItem:
    expected_return_date = _normalize_datetime(loan.expected_return_date)
    days_until_due = max(0, (expected_return_date.date() - now.date()).days)
    return DueLoanNotificationItem(
        loan_id=loan.id,
        user_id=loan.user_id,
        user_email=loan.user.email,
        book_id=loan.book_id,
        book_title=loan.book.title,
        expected_return_date=expected_return_date,
        days_until_due=days_until_due,
    )


def _selected_channels(channel: NotificationChannel) -> list[LoanDueNotificationChannel]:
    if channel == NotificationChannel.EMAIL:
        return [LoanDueNotificationChannel.EMAIL]
    if channel == NotificationChannel.WEBHOOK:
        return [LoanDueNotificationChannel.WEBHOOK]
    return [LoanDueNotificationChannel.EMAIL, LoanDueNotificationChannel.WEBHOOK]


def _build_email_payload(item: DueLoanNotificationItem) -> tuple[str, str]:
    subject = f"Vencimento de empréstimo - {item.book_title}"
    body = (
        f"O empréstimo do livro '{item.book_title}' vence em "
        f"{item.days_until_due} dia(s), na data {item.expected_return_date.date().isoformat()}."
    )
    return subject, body


def _build_webhook_payload(
    *,
    now: datetime,
    days_ahead: int,
    items: list[DueLoanNotificationItem],
) -> dict[str, Any]:
    return {
        "event": "due_loans_notification",
        "generated_at": now.isoformat().replace("+00:00", "Z"),
        "days_ahead": days_ahead,
        "total_due_loans": len(items),
        "loans": [item.model_dump(mode="json") for item in items],
    }


def list_due_loan_notification_items(
    db: Session,
    *,
    days_ahead: int = 1,
    now: datetime | None = None,
) -> list[DueLoanNotificationItem]:
    now = _normalize_datetime(now or datetime.now(timezone.utc))
    end_at = now + timedelta(days=days_ahead)
    loans = loan_due_notification_repository.list_due_active_loans(db, now, end_at)
    return [_loan_to_notification_item(loan, now) for loan in loans]


def _record_delivery(
    db: Session,
    *,
    item: DueLoanNotificationItem,
    channel: LoanDueNotificationChannel,
    status: LoanDueNotificationStatus,
    notification_date,
    error_message: str | None = None,
    skipped: bool = False,
    to: str | None = None,
    subject: str | None = None,
) -> NotificationDeliveryResponse:
    if not skipped:
        loan_due_notification_repository.create_notification(
            db,
            loan_id=item.loan_id,
            channel=channel.value,
            notification_date=notification_date,
            status=status.value,
            error_message=error_message,
        )

    return NotificationDeliveryResponse(
        loan_id=item.loan_id,
        channel=channel.value,
        status=status.value,
        skipped=skipped,
        to=to,
        subject=subject,
        error_message=error_message,
        notification_date=notification_date,
    )


def _dispatch_email(
    db: Session,
    *,
    item: DueLoanNotificationItem,
    notification_date,
) -> NotificationDeliveryResponse:
    subject, body = _build_email_payload(item)
    logger.info(
        "Fake due loan email sent",
        extra={
            "operation": "send_due_loan_notification",
            "channel": LoanDueNotificationChannel.EMAIL.value,
            "loan_id": item.loan_id,
            "to": item.user_email,
            "subject": subject,
            "body": body,
        },
    )
    return _record_delivery(
        db,
        item=item,
        channel=LoanDueNotificationChannel.EMAIL,
        status=LoanDueNotificationStatus.SENT,
        notification_date=notification_date,
        to=item.user_email,
        subject=subject,
    )


def _dispatch_webhook(
    db: Session,
    *,
    item: DueLoanNotificationItem,
    notification_date,
    webhook_url: str | None,
    webhook_success: bool,
    webhook_error: str | None,
) -> NotificationDeliveryResponse:
    if not webhook_url:
        return _record_delivery(
            db,
            item=item,
            channel=LoanDueNotificationChannel.WEBHOOK,
            status=LoanDueNotificationStatus.FAILED,
            notification_date=notification_date,
            error_message="DUE_LOAN_WEBHOOK_URL is not configured.",
        )

    if not webhook_success:
        return _record_delivery(
            db,
            item=item,
            channel=LoanDueNotificationChannel.WEBHOOK,
            status=LoanDueNotificationStatus.FAILED,
            notification_date=notification_date,
            error_message=webhook_error or "Webhook delivery failed.",
        )

    return _record_delivery(
        db,
        item=item,
        channel=LoanDueNotificationChannel.WEBHOOK,
        status=LoanDueNotificationStatus.SENT,
        notification_date=notification_date,
    )


def _send_webhook_batch(webhook_url: str | None, payload: dict[str, Any]) -> tuple[bool, str | None]:
    if not webhook_url:
        return False, "DUE_LOAN_WEBHOOK_URL is not configured."

    try:
        response = httpx.post(webhook_url, json=payload, timeout=WEBHOOK_TIMEOUT_SECONDS)
        response.raise_for_status()
        return True, None
    except httpx.HTTPError as exc:
        logger.warning(
            "Due loan webhook delivery failed",
            extra={"operation": "send_due_loan_notification", "error": str(exc)},
        )
        return False, str(exc)


def send_due_loan_notifications(
    db: Session,
    *,
    days_ahead: int = 1,
    channel: NotificationChannel = NotificationChannel.ALL,
    now: datetime | None = None,
    webhook_url: str | None = None,
) -> DueLoanNotificationResponse:
    now = _normalize_datetime(now or datetime.now(timezone.utc))
    notification_date = now.date()
    webhook_url = webhook_url if webhook_url is not None else os.getenv("DUE_LOAN_WEBHOOK_URL")
    items = list_due_loan_notification_items(db, days_ahead=days_ahead, now=now)
    channels = _selected_channels(channel)
    deliveries: list[NotificationDeliveryResponse] = []

    webhook_success = False
    webhook_error = None
    webhook_pending_items = [
        item
        for item in items
        if loan_due_notification_repository.get_notification(
            db,
            item.loan_id,
            LoanDueNotificationChannel.WEBHOOK.value,
            notification_date,
        )
        is None
    ]
    if LoanDueNotificationChannel.WEBHOOK in channels and webhook_pending_items:
        webhook_success, webhook_error = _send_webhook_batch(
            webhook_url,
            _build_webhook_payload(now=now, days_ahead=days_ahead, items=webhook_pending_items),
        )

    for item in items:
        for selected_channel in channels:
            existing = loan_due_notification_repository.get_notification(
                db,
                item.loan_id,
                selected_channel.value,
                notification_date,
            )
            if existing is not None:
                deliveries.append(
                    _record_delivery(
                        db,
                        item=item,
                        channel=selected_channel,
                        status=LoanDueNotificationStatus(existing.status),
                        notification_date=notification_date,
                        error_message=existing.error_message,
                        skipped=True,
                    )
                )
                continue

            if selected_channel == LoanDueNotificationChannel.EMAIL:
                deliveries.append(_dispatch_email(db, item=item, notification_date=notification_date))
            else:
                deliveries.append(
                    _dispatch_webhook(
                        db,
                        item=item,
                        notification_date=notification_date,
                        webhook_url=webhook_url,
                        webhook_success=webhook_success,
                        webhook_error=webhook_error,
                    )
                )

    return DueLoanNotificationResponse(
        total_due_loans=len(items),
        sent_email_count=sum(
            1
            for delivery in deliveries
            if delivery.channel == LoanDueNotificationChannel.EMAIL.value
            and delivery.status == LoanDueNotificationStatus.SENT.value
            and not delivery.skipped
        ),
        sent_webhook_count=sum(
            1
            for delivery in deliveries
            if delivery.channel == LoanDueNotificationChannel.WEBHOOK.value
            and delivery.status == LoanDueNotificationStatus.SENT.value
            and not delivery.skipped
        ),
        failed_count=sum(1 for delivery in deliveries if delivery.status == LoanDueNotificationStatus.FAILED.value),
        skipped_count=sum(1 for delivery in deliveries if delivery.skipped),
        loans=items,
        deliveries=deliveries,
    )
