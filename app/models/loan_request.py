from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.account import Account
    from app.models.book import Book
    from app.models.loan import Loan
    from app.models.user import User


class LoanRequestType(str, Enum):
    LOAN = "loan"
    RETURN = "return"
    RENEWAL = "renewal"


class LoanRequestStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class LoanRequest(Base):
    __tablename__ = "loan_requests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, nullable=False)
    request_type: Mapped[str] = mapped_column(String, nullable=False, index=True)
    status: Mapped[str] = mapped_column(
        String,
        nullable=False,
        default=LoanRequestStatus.PENDING.value,
        index=True,
    )
    requester_account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"), nullable=False)
    reviewer_account_id: Mapped[int | None] = mapped_column(ForeignKey("accounts.id"), nullable=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    book_id: Mapped[int | None] = mapped_column(ForeignKey("books.id"), nullable=True)
    loan_id: Mapped[int | None] = mapped_column(ForeignKey("loans.id"), nullable=True)
    rejection_reason: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    requester_account: Mapped["Account"] = relationship(
        "Account",
        foreign_keys=[requester_account_id],
    )
    reviewer_account: Mapped["Account | None"] = relationship(
        "Account",
        foreign_keys=[reviewer_account_id],
    )
    user: Mapped["User"] = relationship("User")
    book: Mapped["Book | None"] = relationship("Book")
    loan: Mapped["Loan | None"] = relationship("Loan")

