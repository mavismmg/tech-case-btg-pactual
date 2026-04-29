from sqlalchemy import Column, Integer, Float, ForeignKey, DateTime, Float, String, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base
from datetime import datetime, timedelta, timezone

class Loan(Base):
    __tablename__ = "loans"

    __table_args__ = (
        UniqueConstraint("user_id", "book_id", "status", name="uq_user_book_active_loan"),
    )

    id = Column(Integer, primary_key=True, index=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    book_id = Column(Integer, ForeignKey("books.id"), nullable=False)

    loan_date = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    expected_return_date = Column(DateTime(timezone=True), nullable=False)
    actual_return_date = Column(DateTime(timezone=True), nullable=True)

    fine_value = Column(Float, default=0.0, nullable=False)
    status = Column(String, default="active", nullable=False)

    user = relationship("User", back_populates="loans")
    book = relationship("Book", back_populates="loans")