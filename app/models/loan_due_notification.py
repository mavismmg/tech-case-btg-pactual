from datetime import date, datetime
from enum import Enum

from sqlalchemy import Date, DateTime, ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.core.database import Base
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.loan import Loan


class LoanDueNotificationChannel(str, Enum):
    EMAIL = "email"
    WEBHOOK = "webhook"


class LoanDueNotificationStatus(str, Enum):
    SENT = "sent"
    FAILED = "failed"


class LoanDueNotification(Base):
    __tablename__ = "loan_due_notifications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, nullable=False)
    loan_id: Mapped[int] = mapped_column(ForeignKey("loans.id"), nullable=False, index=True)
    channel: Mapped[str] = mapped_column(String, nullable=False, index=True)
    notification_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    status: Mapped[str] = mapped_column(String, nullable=False, index=True)
    error_message: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint(
            "loan_id",
            "channel",
            "notification_date",
            name="uq_loan_due_notifications_loan_channel_date",
        ),
        Index("ix_loan_due_notifications_channel_date", "channel", "notification_date"),
        Index("ix_loan_due_notifications_status_created_at", "status", "created_at"),
    )

    loan: Mapped["Loan"] = relationship("Loan")
