from datetime import date, datetime, timedelta, timezone

import pytest

from app.models.account import AccountRole
from app.models.loan_operation_metric import LoanMetricOperation, LoanOperationMetric
from app.models.loan_request import LoanRequestStatus, LoanRequestType
from app.repositories.loan_repository import get_active_loans_count_by_user_id
from app.schemas.account import AccountCreate
from app.schemas.author import AuthorCreate
from app.schemas.book import BookCreate
from app.schemas.user import UserCreate
from app.services.account_service import create_account
from app.services.author_service import create_author
from app.services.book_service import create_book
from app.services.loan_request_service import (
    DuplicatePendingLoanRequestError,
    LoanRequestApprovalError,
    create_loan_action_request,
    create_loan_request,
    approve_loan_request,
    reject_loan_request,
)
from app.services.loan_service import create_loan
from app.services.user_service import create_user


def _staff_account(db):
    return create_account(
        db,
        AccountCreate(
            name="Admin",
            email="admin@example.com",
            password="strong-password",
            role=AccountRole.ADMIN,
        ),
    )


def _reader_account(db):
    user = create_user(db, UserCreate(name="Reader", email="reader@example.com"))
    account = create_account(
        db,
        AccountCreate(
            name="Reader Account",
            email="reader-account@example.com",
            password="strong-password",
            role=AccountRole.READER,
            user_id=user.id,
        ),
    )
    return user, account


def _book(db):
    author = create_author(db, AuthorCreate(name="Test Author"))
    return create_book(
        db,
        BookCreate(
            isbn="1234567890",
            author_id=author.id,
            title="Test Book",
            published_date=date(2023, 1, 1),
        ),
    )


def test_reader_creates_pending_loan_request(db):
    user, reader = _reader_account(db)
    book = _book(db)

    loan_request = create_loan_request(db, reader, book.id)

    assert loan_request.status == LoanRequestStatus.PENDING
    assert loan_request.request_type == LoanRequestType.LOAN
    assert loan_request.user_id == user.id
    assert loan_request.book_id == book.id

    metric = (
        db.query(LoanOperationMetric)
        .filter(
            LoanOperationMetric.operation == LoanMetricOperation.LOAN_REQUEST_CREATED.value,
            LoanOperationMetric.loan_request_id == loan_request.id,
        )
        .one()
    )
    assert metric.user_id == user.id
    assert metric.book_id == book.id


def test_reader_cannot_create_duplicate_pending_loan_request(db):
    _, reader = _reader_account(db)
    book = _book(db)
    create_loan_request(db, reader, book.id)

    with pytest.raises(DuplicatePendingLoanRequestError):
        create_loan_request(db, reader, book.id)


def test_staff_approves_loan_request_and_creates_active_loan(db):
    user, reader = _reader_account(db)
    staff = _staff_account(db)
    book = _book(db)
    loan_request = create_loan_request(db, reader, book.id)

    approved_request = approve_loan_request(db, loan_request.id, staff)

    assert approved_request.status == LoanRequestStatus.APPROVED
    assert approved_request.reviewer_account_id == staff.id
    assert get_active_loans_count_by_user_id(db, user.id) == 1
    db.refresh(book)
    assert book.is_available is False

    approval_metric = (
        db.query(LoanOperationMetric)
        .filter(
            LoanOperationMetric.operation == LoanMetricOperation.LOAN_REQUEST_APPROVED.value,
            LoanOperationMetric.loan_request_id == approved_request.id,
        )
        .one()
    )
    assert approval_metric.reviewer_account_id == staff.id


def test_staff_rejects_loan_request_without_creating_loan(db):
    user, reader = _reader_account(db)
    staff = _staff_account(db)
    book = _book(db)
    loan_request = create_loan_request(db, reader, book.id)

    rejected_request = reject_loan_request(db, loan_request.id, staff, "Book reserved for maintenance")

    assert rejected_request.status == LoanRequestStatus.REJECTED
    assert rejected_request.rejection_reason == "Book reserved for maintenance"
    assert get_active_loans_count_by_user_id(db, user.id) == 0
    db.refresh(book)
    assert book.is_available is True

    rejection_metric = (
        db.query(LoanOperationMetric)
        .filter(
            LoanOperationMetric.operation == LoanMetricOperation.LOAN_REQUEST_REJECTED.value,
            LoanOperationMetric.loan_request_id == rejected_request.id,
        )
        .one()
    )
    assert rejection_metric.reviewer_account_id == staff.id


def test_staff_approves_return_request_and_returns_loan(db):
    user, reader = _reader_account(db)
    staff = _staff_account(db)
    book = _book(db)
    loan = create_loan(db, user.id, book.id)
    loan_request = create_loan_action_request(db, reader, loan.id, LoanRequestType.RETURN)

    approved_request = approve_loan_request(db, loan_request.id, staff)

    assert approved_request.status == LoanRequestStatus.APPROVED
    db.refresh(loan)
    assert loan.status == "returned"
    db.refresh(book)
    assert book.is_available is True

    return_metric = (
        db.query(LoanOperationMetric)
        .filter(
            LoanOperationMetric.operation == LoanMetricOperation.LOAN_RETURNED.value,
            LoanOperationMetric.loan_id == loan.id,
        )
        .one()
    )
    assert return_metric.fine_value == 0.0


def test_staff_approves_renewal_request_and_extends_loan(db):
    user, reader = _reader_account(db)
    staff = _staff_account(db)
    book = _book(db)
    loan = create_loan(db, user.id, book.id)
    original_expected_return_date = loan.expected_return_date
    loan_request = create_loan_action_request(db, reader, loan.id, LoanRequestType.RENEWAL)

    approved_request = approve_loan_request(db, loan_request.id, staff)

    assert approved_request.status == LoanRequestStatus.APPROVED
    db.refresh(loan)
    assert loan.expected_return_date == original_expected_return_date + timedelta(days=14)
    assert loan.renewal_count == 1

    renewal_metric = (
        db.query(LoanOperationMetric)
        .filter(
            LoanOperationMetric.operation == LoanMetricOperation.LOAN_RENEWED.value,
            LoanOperationMetric.loan_id == loan.id,
        )
        .one()
    )
    assert renewal_metric.user_id == user.id


def test_second_renewal_is_blocked(db):
    user, reader = _reader_account(db)
    staff = _staff_account(db)
    book = _book(db)
    loan = create_loan(db, user.id, book.id)
    first_request = create_loan_action_request(db, reader, loan.id, LoanRequestType.RENEWAL)
    approve_loan_request(db, first_request.id, staff)

    second_request = create_loan_action_request(db, reader, loan.id, LoanRequestType.RENEWAL)

    with pytest.raises(LoanRequestApprovalError):
        approve_loan_request(db, second_request.id, staff)


def test_overdue_renewal_is_blocked(db):
    user, reader = _reader_account(db)
    staff = _staff_account(db)
    book = _book(db)
    loan = create_loan(db, user.id, book.id)
    loan.expected_return_date = datetime.now(timezone.utc) - timedelta(days=1)
    db.commit()
    renewal_request = create_loan_action_request(db, reader, loan.id, LoanRequestType.RENEWAL)

    with pytest.raises(LoanRequestApprovalError):
        approve_loan_request(db, renewal_request.id, staff)
