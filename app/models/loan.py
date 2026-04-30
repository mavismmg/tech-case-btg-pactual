from datetime import datetime
from enum import Enum

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String
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

    __table_args__ = (
        Index(
            "ix_loans_active_user_book",
            "user_id",
            "book_id",
            unique=True,
            postgresql_where=status == LoanStatus.ACTIVE.value,
        ),
    )

    user: Mapped["User"] = relationship("User", back_populates="loans")
    book: Mapped["Book"] = relationship("Book", back_populates="loans")
