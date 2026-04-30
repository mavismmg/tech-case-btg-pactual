import pytest
from datetime import date

from app.schemas.author import AuthorCreate
from app.schemas.book import BookCreate
from app.schemas.user import UserCreate
from app.services.author_service import create_author
from app.services.book_service import create_book
from app.services.loan_service import create_loan
from app.services.user_service import (
    UserHasActiveLoansError,
    UserNotFoundError,
    create_user,
    delete_user,
    get_user_by_id,
)

def test_create_user(db):
    user_data = UserCreate(name="Test User", email="test@example.com")
    user = create_user(db, user_data)
    
    assert user.name == "Test User"
    assert user.email == "test@example.com"
    assert user.id is not None

def test_get_user_by_id(db):
    user_data = UserCreate(name="Test User", email="test@example.com")
    created_user = create_user(db, user_data)
    
    user = get_user_by_id(db, created_user.id)
    assert user is not None
    assert user.id == created_user.id
    assert user.name == "Test User"

def test_get_user_by_id_not_found(db):
    with pytest.raises(UserNotFoundError):
        get_user_by_id(db, 999)

def test_create_user_restores_soft_deleted_user_with_same_email(db):
    user_data = UserCreate(name="Test User", email="test@example.com")
    deleted_user = create_user(db, user_data)
    deleted_user_id = deleted_user.id

    delete_user(db, deleted_user.id)

    restored_user = create_user(db, UserCreate(name="Second User", email="test@example.com"))

    assert restored_user.id == deleted_user_id
    assert restored_user.name == "Second User"
    assert restored_user.email == "test@example.com"
    assert restored_user.deleted_at is None
    assert restored_user.is_active is True

def test_delete_user_with_active_loan_fails(db):
    user = create_user(db, UserCreate(name="Test User", email="test@example.com"))
    author = create_author(db, AuthorCreate(name="Test Author"))
    book = create_book(
        db,
        BookCreate(
            isbn="1234567890",
            author_id=author.id,
            title="Test Book",
            published_date=date(2023, 1, 1),
        ),
    )
    create_loan(db, user.id, book.id)

    with pytest.raises(UserHasActiveLoansError):
        delete_user(db, user.id)
