from datetime import datetime
from enum import Enum

from sqlalchemy import DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from app.core.database import Base
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.user import User # Import only visible for pylance 
    from app.models.book import Book # Import only visible for pylance

class LoanStatus(str, Enum):
    ACTIVE = "active"
    RETURNED = "returned"

class Loan(Base):
    __tablename__ = "loans"

    __table_args__ = (
        UniqueConstraint("user_id", "book_id", "status", name="uq_user_book_active_loan"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    book_id: Mapped[int] = mapped_column(ForeignKey("books.id"), nullable=False)

    loan_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    expected_return_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    actual_return_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    fine_value: Mapped[float] = mapped_column(default=0.0, nullable=False)
    status: Mapped[str] = mapped_column(String, default="active", nullable=False)

    user: Mapped["User"] = relationship("User", back_populates="loans")
    book: Mapped["Book"] = relationship("Book", back_populates="loans")