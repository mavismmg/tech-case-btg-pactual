from datetime import date
from pathlib import Path
import sys

from sqlalchemy.orm import Session

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import app.models
from app.core.database import SessionLocal
from app.models.account import AccountRole
from app.models.book import Book
from app.repositories import account_repository, author_repository, user_repository
from app.schemas.account import AccountCreate
from app.schemas.author import AuthorCreate
from app.schemas.book import BookCreate
from app.schemas.user import UserCreate
from app.services.account_service import create_account
from app.services.author_service import create_author
from app.services.book_service import create_book
from app.services.user_service import create_user

DEFAULT_PASSWORD = "12345678"


def get_or_create_user(db: Session, name: str, email: str):
    user = user_repository.get_user_by_email(db, email)
    if user is not None:
        return user

    return create_user(db, UserCreate(name=name, email=email))


def get_or_create_account(
    db: Session,
    name: str,
    email: str,
    role: AccountRole,
    user_id: int | None = None,
):
    account = account_repository.get_account_by_email(db, email)
    if account is not None:
        return account

    return create_account(
        db,
        AccountCreate(
            name=name,
            email=email,
            password=DEFAULT_PASSWORD,
            role=role,
            user_id=user_id,
        ),
    )


def get_or_create_author(db: Session, name: str):
    author = author_repository.get_author_by_name(db, name)
    if author is not None:
        return author

    return create_author(db, AuthorCreate(name=name))


def get_or_create_book(
    db: Session,
    isbn: str,
    author_id: int,
    title: str,
    published_date: date,
):
    book = (
        db.query(Book)
        .filter(
            Book.isbn == isbn,
            Book.author_id == author_id,
            Book.title == title,
            Book.deleted_at.is_(None),
        )
        .first()
    )
    if book is not None:
        return book

    return create_book(
        db,
        BookCreate(
            isbn=isbn,
            author_id=author_id,
            title=title,
            published_date=published_date,
        ),
    )


def seed() -> None:
    db = SessionLocal()
    try:
        admin = get_or_create_account(
            db,
            name="Admin",
            email="admin@example.com",
            role=AccountRole.ADMIN,
        )
        librarian = get_or_create_account(
            db,
            name="Librarian",
            email="librarian@example.com",
            role=AccountRole.LIBRARIAN,
        )
        reader_user = get_or_create_user(db, name="Reader", email="reader@example.com")
        reader_account = get_or_create_account(
            db,
            name="Reader Account",
            email="reader-account@example.com",
            role=AccountRole.READER,
            user_id=reader_user.id,
        )

        machado = get_or_create_author(db, "Machado de Assis")
        orwell = get_or_create_author(db, "George Orwell")

        get_or_create_book(db, "9788535914849", machado.id, "Dom Casmurro", date(1899, 1, 1))
        get_or_create_book(db, "9788535910667", machado.id, "Memorias Postumas de Bras Cubas", date(1881, 1, 1))
        get_or_create_book(db, "9780451524935", orwell.id, "1984", date(1949, 6, 8))

        print("Development seed completed.")
        print("")
        print("Accounts:")
        print(f"- admin: {admin.email} / {DEFAULT_PASSWORD}")
        print(f"- librarian: {librarian.email} / {DEFAULT_PASSWORD}")
        print(f"- reader: {reader_account.email} / {DEFAULT_PASSWORD}")
        print("")
        print("Suggested flow:")
        print("1. Login as reader and create a loan request.")
        print("2. Login as admin/librarian and approve the request.")
        print("3. Return the loan and inspect /metrics/loans.")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
