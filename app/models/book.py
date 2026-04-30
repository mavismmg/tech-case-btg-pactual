from datetime import datetime, date

from sqlalchemy import Date, ForeignKey, Integer, String, Boolean, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from app.core.database import Base
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.author import Author # Import only visible for pylance 
    from app.models.loan import Loan # Import only visible for pylance

class Book(Base):
    __tablename__ = "books"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, nullable=False)
    isbn: Mapped[str] = mapped_column(String, index=True, nullable=False)
    author_id: Mapped[int] = mapped_column(ForeignKey("authors.id"), nullable=False)
    title: Mapped[str] = mapped_column(String, index=True, nullable=False)

    published_date: Mapped[date] = mapped_column(Date, nullable=False)

    is_available: Mapped[bool] = mapped_column(Boolean, default=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
    
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        onupdate=func.now(),
        nullable=True
    )

    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )

    author: Mapped["Author"] = relationship("Author", back_populates="books")
    loans: Mapped[list["Loan"]] = relationship("Loan", back_populates="book")
