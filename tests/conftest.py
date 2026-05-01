import os
from collections.abc import Callable
from datetime import date, datetime, timedelta, timezone
from itertools import count
from urllib.parse import urlparse

import pytest
from dotenv import load_dotenv

load_dotenv()

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import app.core.rate_limit as rate_limit_module
from app.core.database import Base
from app.dependencies import get_db
import app.models
from app.models.account import Account, AccountRole
from app.models.author import Author
from app.models.book import Book
from app.models.loan import Loan
from app.models.user import User
from app.server import app
from app.schemas.account import AccountCreate
from app.schemas.author import AuthorCreate
from app.schemas.book import BookCreate
from app.schemas.user import UserCreate
from app.services.account_service import create_account
from app.services.author_service import create_author
from app.services.book_service import create_book
from app.services.loan_service import create_loan, return_loan
from app.services.user_service import create_user

TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL")
DATABASE_URL = os.getenv("DATABASE_URL")
if TEST_DATABASE_URL is None:
    raise RuntimeError("TEST_DATABASE_URL must be set for tests")

if DATABASE_URL is not None and TEST_DATABASE_URL == DATABASE_URL:
    raise RuntimeError("TEST_DATABASE_URL must be different from DATABASE_URL")

parsed_test_database_url = urlparse(TEST_DATABASE_URL)
if "test" not in parsed_test_database_url.path.lower():
    raise RuntimeError("TEST_DATABASE_URL must point to a dedicated test database")

engine = create_engine(TEST_DATABASE_URL)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="function")
def db():
    Base.metadata.create_all(bind=engine)
    
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db):
    def override_get_db():
        try:
            yield db
        finally:
            pass

    previous_rate_limit_enabled = rate_limit_module.RATE_LIMIT_ENABLED
    rate_limit_module.RATE_LIMIT_ENABLED = False
    app.dependency_overrides[get_db] = override_get_db

    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()
        rate_limit_module.RATE_LIMIT_ENABLED = previous_rate_limit_enabled


@pytest.fixture(scope="function")
def unique_suffix() -> Callable[[str], str]:
    sequence = count(1)

    def build(prefix: str) -> str:
        return f"{prefix}-{next(sequence)}"

    return build


@pytest.fixture(scope="function")
def user_factory(db, unique_suffix) -> Callable[..., User]:
    def create(**overrides):
        suffix = unique_suffix("user")
        data = {
            "name": f"Test User {suffix}",
            "email": f"{suffix}@example.com",
        }
        data.update(overrides)
        return create_user(db, UserCreate(**data))

    return create


@pytest.fixture(scope="function")
def author_factory(db, unique_suffix) -> Callable[..., Author]:
    def create(**overrides):
        suffix = unique_suffix("author")
        data = {"name": f"Test Author {suffix}"}
        data.update(overrides)
        return create_author(db, AuthorCreate(**data))

    return create


@pytest.fixture(scope="function")
def book_factory(db, author_factory, unique_suffix) -> Callable[..., Book]:
    def create(**overrides):
        author = overrides.pop("author", None)
        author_id = overrides.pop("author_id", None)
        if author_id is None:
            author_id = author.id if author is not None else author_factory().id

        suffix = unique_suffix("book")
        numeric_suffix = "".join(char for char in suffix if char.isdigit()).rjust(3, "0")
        data = {
            "isbn": f"1234567{numeric_suffix}",
            "author_id": author_id,
            "title": f"Test Book {suffix}",
            "published_date": date(2023, 1, 1),
        }
        data.update(overrides)
        return create_book(db, BookCreate(**data))

    return create


@pytest.fixture(scope="function")
def account_factory(db, user_factory, unique_suffix) -> Callable[..., Account]:
    def create(**overrides):
        suffix = unique_suffix("account")
        role = overrides.pop("role", AccountRole.LIBRARIAN)
        user_id = overrides.pop("user_id", None)
        if role == AccountRole.READER and user_id is None:
            user_id = user_factory().id

        data = {
            "name": f"Test Account {suffix}",
            "email": f"{suffix}@example.com",
            "password": "strong-password",
            "role": role,
            "user_id": user_id,
        }
        data.update(overrides)
        return create_account(db, AccountCreate(**data))

    return create


@pytest.fixture(scope="function")
def loan_factory(db, user_factory, book_factory) -> Callable[..., Loan]:
    def create(**overrides):
        user = overrides.pop("user", None)
        book = overrides.pop("book", None)
        user_id = overrides.pop("user_id", user.id if user is not None else user_factory().id)
        book_id = overrides.pop("book_id", book.id if book is not None else book_factory().id)
        loan = create_loan(db, user_id, book_id)

        for field, value in overrides.items():
            setattr(loan, field, value)

        if overrides:
            db.commit()
            db.refresh(loan)

        return loan

    return create


@pytest.fixture(scope="function")
def active_loan_factory(loan_factory) -> Callable[..., Loan]:
    return loan_factory


@pytest.fixture(scope="function")
def returned_loan_factory(db, loan_factory) -> Callable[..., Loan]:
    def create(**overrides):
        loan = loan_factory(**overrides)
        return return_loan(db, loan.id)

    return create


@pytest.fixture(scope="function")
def overdue_loan_factory(db, loan_factory) -> Callable[..., Loan]:
    def create(**overrides):
        days_overdue = overrides.pop("days_overdue", 1)
        loan = loan_factory(**overrides)
        loan.expected_return_date = datetime.now(timezone.utc) - timedelta(days=days_overdue)
        db.commit()
        db.refresh(loan)
        return loan

    return create


def _login(client, email: str, password: str = "strong-password") -> str:
    response = client.post("/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200
    return response.json()["access_token"]


@pytest.fixture(scope="function")
def admin_headers(client) -> dict[str, str]:
    response = client.post(
        "/auth/bootstrap",
        json={"name": "Admin", "email": "admin@example.com", "password": "strong-password"},
    )
    assert response.status_code == 201
    token = _login(client, "admin@example.com")
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="function")
def librarian_headers(client, account_factory) -> dict[str, str]:
    account = account_factory(role=AccountRole.LIBRARIAN)
    token = _login(client, account.email)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="function")
def reader_headers(client, account_factory) -> dict[str, str]:
    account = account_factory(role=AccountRole.READER)
    token = _login(client, account.email)
    return {"Authorization": f"Bearer {token}"}
