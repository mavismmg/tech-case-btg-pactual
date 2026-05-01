from datetime import date, datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, field_serializer


class NotificationChannel(str, Enum):
    EMAIL = "email"
    WEBHOOK = "webhook"
    ALL = "all"


class NotificationDeliveryResponse(BaseModel):
    loan_id: int
    channel: str
    status: str
    skipped: bool = False
    to: str | None = None
    subject: str | None = None
    error_message: str | None = None
    notification_date: date

    model_config = ConfigDict(from_attributes=True)


class DueLoanNotificationItem(BaseModel):
    loan_id: int
    user_id: int
    user_email: str
    book_id: int
    book_title: str
    expected_return_date: datetime
    days_until_due: int = Field(..., ge=0)

    @field_serializer("expected_return_date")
    def serialize_datetime(self, value: datetime) -> str:
        return value.isoformat().replace("+00:00", "Z")


class DueLoanNotificationResponse(BaseModel):
    total_due_loans: int
    sent_email_count: int
    sent_webhook_count: int
    failed_count: int
    skipped_count: int
    loans: list[DueLoanNotificationItem]
    deliveries: list[NotificationDeliveryResponse]
