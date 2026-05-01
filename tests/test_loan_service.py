import logging
from datetime import date, datetime, timedelta, timezone
from enum import Enum

import pytest
import app.services.loan_service as loan_service_module
from app.models.loan import LoanStatus
from app.services.user_service import create_user
from app.services.author_service import create_author
from app.services.book_service import create_book
from app.services.loan_service import (
    _calculate_fine_value,
    _calculate_overdue_days,
    create_loan,
    list_active_loans,
    list_loans,
    list_overdue_loans,
    return_loan,
    LoanAlreadyReturnedError,
)
from app.schemas.user import UserCreate
from app.schemas.author import AuthorCreate
from app.schemas.book import BookCreate

class LoanStatusMock(str, Enum):
    ACTIVE = "active"
    RETURNED = "returned"


def test_calculate_fine_uses_only_full_overdue_days():
    actual_return_date = datetime(2026, 5, 15, 12, 0, tzinfo=timezone.utc)

    assert _calculate_overdue_days(actual_return_date, actual_return_date) == 0
    assert _calculate_fine_value(0) == 0.0

    one_day_late = actual_return_date - timedelta(days=1)
    assert _calculate_overdue_days(one_day_late, actual_return_date) == 1
    assert _calculate_fine_value(1) == 2.0

    partial_day_late = actual_return_date - timedelta(hours=23, minutes=59)
    assert _calculate_overdue_days(partial_day_late, actual_return_date) == 0
    assert _calculate_fine_value(0) == 0.0

    fourteen_days_and_two_hours_late = actual_return_date - timedelta(days=14, hours=2)
    assert _calculate_overdue_days(fourteen_days_and_two_hours_late, actual_return_date) == 14
    assert _calculate_fine_value(14) == 28.0


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


def test_list_loans_filters_by_status_user_and_overdue(db):
    user = create_user(db, UserCreate(name="Filter User", email="filter@example.com"))
    second_user = create_user(db, UserCreate(name="Second User", email="second@example.com"))
    author = create_author(db, AuthorCreate(name="Filter Author"))
    active_book = create_book(
        db,
        BookCreate(
            isbn="1234567890",
            author_id=author.id,
            title="Active Book",
            published_date=date(2023, 1, 1),
        ),
    )
    overdue_book = create_book(
        db,
        BookCreate(
            isbn="1234567891",
            author_id=author.id,
            title="Overdue Book",
            published_date=date(2023, 1, 1),
        ),
    )
    returned_book = create_book(
        db,
        BookCreate(
            isbn="1234567892",
            author_id=author.id,
            title="Returned Book",
            published_date=date(2023, 1, 1),
        ),
    )
    second_user_book = create_book(
        db,
        BookCreate(
            isbn="1234567893",
            author_id=author.id,
            title="Second User Book",
            published_date=date(2023, 1, 1),
        ),
    )

    active_loan = create_loan(db, user.id, active_book.id)
    overdue_loan = create_loan(db, user.id, overdue_book.id)
    returned_loan = create_loan(db, user.id, returned_book.id)
    create_loan(db, second_user.id, second_user_book.id)

    overdue_loan.expected_return_date = datetime.now(timezone.utc) - timedelta(days=2)
    db.commit()
    return_loan(db, returned_loan.id)

    all_loans, all_total = list_loans(db)
    assert all_total == 4
    assert len(all_loans) == 4

    active_loans, active_total = list_loans(db, status=LoanStatus.ACTIVE)
    assert active_total == 3
    assert {loan.status for loan in active_loans} == {"active"}

    returned_loans, returned_total = list_loans(db, status=LoanStatus.RETURNED)
    assert returned_total == 1
    assert returned_loans[0].id == returned_loan.id

    user_loans, user_total = list_loans(db, user_id=user.id)
    assert user_total == 3
    assert {loan.user_id for loan in user_loans} == {user.id}

    overdue_loans, overdue_total = list_loans(db, overdue=True)
    assert overdue_total == 1
    assert overdue_loans[0].id == overdue_loan.id

    active_endpoint_loans, active_endpoint_total = list_active_loans(db)
    assert active_endpoint_total == 3
    assert active_loan.id in {loan.id for loan in active_endpoint_loans}

    overdue_endpoint_loans, overdue_endpoint_total = list_overdue_loans(db)
    assert overdue_endpoint_total == 1
    assert overdue_endpoint_loans[0].id == overdue_loan.id
