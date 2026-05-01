from datetime import datetime
from enum import Enum

from sqlalchemy import DateTime, Float, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.core.database import Base


class LoanMetricOperation(str, Enum):
    LOAN_REQUEST_CREATED = "loan_request_created"
    LOAN_REQUEST_APPROVED = "loan_request_approved"
    LOAN_REQUEST_REJECTED = "loan_request_rejected"
    LOAN_CREATED = "loan_created"
    LOAN_RETURNED = "loan_returned"
    LOAN_RENEWED = "loan_renewed"


class LoanOperationMetric(Base):
    __tablename__ = "loan_operation_metrics"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, nullable=False)
    operation: Mapped[str] = mapped_column(String, nullable=False, index=True)
    loan_id: Mapped[int | None] = mapped_column(ForeignKey("loans.id"), nullable=True, index=True)
    loan_request_id: Mapped[int | None] = mapped_column(ForeignKey("loan_requests.id"), nullable=True, index=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    book_id: Mapped[int | None] = mapped_column(ForeignKey("books.id"), nullable=True, index=True)
    account_id: Mapped[int | None] = mapped_column(ForeignKey("accounts.id"), nullable=True, index=True)
    reviewer_account_id: Mapped[int | None] = mapped_column(ForeignKey("accounts.id"), nullable=True, index=True)
    fine_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        Index("ix_loan_operation_metrics_operation_created_at", "operation", "created_at"),
    )
