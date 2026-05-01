import logging
from datetime import date
from enum import Enum

import pytest
import app.services.loan_service as loan_service_module
from app.services.user_service import create_user
from app.services.author_service import create_author
from app.services.book_service import create_book
from app.services.loan_service import create_loan, return_loan, LoanAlreadyReturnedError
from app.schemas.user import UserCreate
from app.schemas.author import AuthorCreate
from app.schemas.book import BookCreate

class LoanStatusMock(str, Enum):
    ACTIVE = "active"
    RETURNED = "returned"

def test_create_loan(db, caplog):
    user_data = UserCreate(name="Test User", email="test@example.com")
    user = create_user(db, user_data)
    
    author_data = AuthorCreate(name="Test Author")
    author = create_author(db, author_data)
    
    book_data = BookCreate(isbn="1234567890", author_id=author.id, title="Test Book", published_date=date(2023, 1, 1))
    book = create_book(db, book_data)
    
    with caplog.at_level(logging.INFO, logger="app.services.loan_service"):
        loan = create_loan(db, user.id, book.id)
    
    assert loan.user_id == user.id
    assert loan.book_id == book.id
    assert loan.status == LoanStatusMock.ACTIVE
    assert loan.fine_value == 0.0
    db.refresh(book)
    assert book.is_available is False

    log_record = next(
        record for record in caplog.records if record.message == "Loan created successfully"
    )
    assert log_record.operation == "create_loan"
    assert log_record.user_id == user.id
    assert log_record.book_id == book.id
    assert log_record.loan_id == loan.id

def test_return_loan(db):
    user_data = UserCreate(name="Test User", email="test@example.com")
    user = create_user(db, user_data)
    
    author_data = AuthorCreate(name="Test Author")
    author = create_author(db, author_data)
    
    book_data = BookCreate(isbn="1234567890", author_id=author.id, title="Test Book", published_date=date(2023, 1, 1))
    book = create_book(db, book_data)
    
    loan = create_loan(db, user.id, book.id)
    
    returned_loan = return_loan(db, loan.id)
    
    assert returned_loan.status == LoanStatusMock.RETURNED
    assert returned_loan.actual_return_date is not None
    assert returned_loan.fine_value == 0.0

    second_loan = create_loan(db, user.id, book.id)
    second_returned_loan = return_loan(db, second_loan.id)

    assert second_returned_loan.status == LoanStatusMock.RETURNED
    assert second_returned_loan.actual_return_date is not None

def test_return_loan_already_returned(db, caplog):
    user_data = UserCreate(name="Test User", email="test@example.com")
    user = create_user(db, user_data)
    
    author_data = AuthorCreate(name="Test Author")
    author = create_author(db, author_data)
    
    book_data = BookCreate(isbn="1234567890", author_id=author.id, title="Test Book", published_date=date(2023, 1, 1))
    book = create_book(db, book_data)
    
    loan = create_loan(db, user.id, book.id)
    return_loan(db, loan.id)
    
    with caplog.at_level(logging.WARNING, logger="app.services.loan_service"):
        with pytest.raises(LoanAlreadyReturnedError):
            return_loan(db, loan.id)

    warning_record = next(
        record for record in caplog.records if record.message == "Loan return blocked because loan is not active"
    )
    assert warning_record.levelno == logging.WARNING
    assert warning_record.operation == "return_loan"
    assert warning_record.loan_id == loan.id
    assert warning_record.reason == "loan_not_active"
    assert not any(record.levelno >= logging.ERROR for record in caplog.records)


def test_create_loan_logs_unexpected_error(db, monkeypatch, caplog):
    user_data = UserCreate(name="Test User", email="test@example.com")
    user = create_user(db, user_data)

    author_data = AuthorCreate(name="Test Author")
    author = create_author(db, author_data)

    book_data = BookCreate(isbn="1234567890", author_id=author.id, title="Test Book", published_date=date(2023, 1, 1))
    book = create_book(db, book_data)

    def fail_to_get_book(*args, **kwargs):
        raise RuntimeError("database exploded")

    monkeypatch.setattr(loan_service_module.book_repository, "get_book_by_id", fail_to_get_book)

    with caplog.at_level(logging.ERROR, logger="app.services.loan_service"):
        with pytest.raises(RuntimeError):
            create_loan(db, user.id, book.id)

    error_record = next(
        record for record in caplog.records if record.message == "Unexpected error while creating loan"
    )
    assert error_record.levelno == logging.ERROR
    assert error_record.exc_info is not None
    assert error_record.operation == "create_loan"
    assert error_record.user_id == user.id
    assert error_record.book_id == book.id
