from datetime import datetime, timedelta, timezone

import pytest

from app.models.loan import LoanStatus
from app.services.loan_service import (
    LoanAlreadyReturnedError,
    LoanBookIsNotAvailableError,
    LoanLimitExceededError,
    LoanRenewalNotAllowedError,
    _calculate_fine_value,
    _calculate_overdue_days,
    create_loan,
    renew_loan,
    return_loan,
)


@pytest.mark.parametrize(
    ("expected_return_date", "actual_return_date", "expected_days", "expected_fine"),
    [
        (
            datetime(2026, 5, 1, 12, 0, tzinfo=timezone.utc),
            datetime(2026, 5, 1, 12, 0, tzinfo=timezone.utc),
            0,
            0.0,
        ),
        (
            datetime(2026, 5, 1, 12, 0, tzinfo=timezone.utc),
            datetime(2026, 5, 1, 11, 0, tzinfo=timezone.utc),
            0,
            0.0,
        ),
        (
            datetime(2026, 5, 1, 12, 0, tzinfo=timezone.utc),
            datetime(2026, 5, 2, 12, 0, tzinfo=timezone.utc),
            1,
            2.0,
        ),
        (
            datetime(2026, 5, 1, 12, 0, tzinfo=timezone.utc),
            datetime(2026, 5, 15, 14, 0, tzinfo=timezone.utc),
            14,
            28.0,
        ),
        (
            datetime(2026, 5, 1, 12, 0, tzinfo=timezone.utc),
            datetime(2026, 5, 2, 11, 59, tzinfo=timezone.utc),
            0,
            0.0,
        ),
    ],
)
def test_fine_calculation_uses_full_overdue_days_and_is_never_negative(
    expected_return_date,
    actual_return_date,
    expected_days,
    expected_fine,
):
    overdue_days = _calculate_overdue_days(expected_return_date, actual_return_date)

    assert overdue_days == expected_days
    assert overdue_days >= 0
    assert _calculate_fine_value(overdue_days) == expected_fine


@pytest.mark.parametrize("active_loan_count", [0, 1, 2])
def test_user_can_create_loan_until_active_limit(db, user_factory, book_factory, active_loan_count):
    user = user_factory()
    for _ in range(active_loan_count):
        create_loan(db, user.id, book_factory().id)

    loan = create_loan(db, user.id, book_factory().id)

    assert loan.status == LoanStatus.ACTIVE


def test_user_with_three_active_loans_cannot_create_fourth(db, user_factory, book_factory):
    user = user_factory()
    for _ in range(3):
        create_loan(db, user.id, book_factory().id)

    with pytest.raises(LoanLimitExceededError):
        create_loan(db, user.id, book_factory().id)


def test_returned_loans_do_not_count_towards_active_loan_limit(db, user_factory, book_factory):
    user = user_factory()
    returned = create_loan(db, user.id, book_factory().id)
    return_loan(db, returned.id)

    for _ in range(3):
        create_loan(db, user.id, book_factory().id)

    with pytest.raises(LoanLimitExceededError):
        create_loan(db, user.id, book_factory().id)


def test_available_book_can_be_loaned_and_returned_book_becomes_available(db, user_factory, book_factory):
    user = user_factory()
    book = book_factory()

    loan = create_loan(db, user.id, book.id)
    db.refresh(book)
    assert loan.status == LoanStatus.ACTIVE
    assert book.is_available is False

    returned = return_loan(db, loan.id)
    db.refresh(book)
    assert returned.status == LoanStatus.RETURNED
    assert returned.actual_return_date is not None
    assert book.is_available is True


def test_unavailable_book_cannot_be_loaned_again(db, user_factory, book_factory):
    first_user = user_factory()
    second_user = user_factory()
    book = book_factory()
    create_loan(db, first_user.id, book.id)

    with pytest.raises(LoanBookIsNotAvailableError):
        create_loan(db, second_user.id, book.id)


def test_returning_loan_twice_is_invalid(db, active_loan_factory):
    loan = active_loan_factory()
    return_loan(db, loan.id)

    with pytest.raises(LoanAlreadyReturnedError):
        return_loan(db, loan.id)


def test_renewal_extends_active_non_overdue_loan_once(db, active_loan_factory):
    loan = active_loan_factory()
    original_expected_return_date = loan.expected_return_date

    renewed = renew_loan(db, loan.id)

    assert renewed.expected_return_date == original_expected_return_date + timedelta(days=14)
    assert renewed.renewal_count == 1


def test_second_renewal_is_invalid(db, active_loan_factory):
    loan = active_loan_factory()
    renew_loan(db, loan.id)

    with pytest.raises(LoanRenewalNotAllowedError):
        renew_loan(db, loan.id)


def test_overdue_or_returned_loan_cannot_be_renewed(db, overdue_loan_factory, returned_loan_factory):
    overdue_loan = overdue_loan_factory()
    returned_loan = returned_loan_factory()

    with pytest.raises(LoanRenewalNotAllowedError):
        renew_loan(db, overdue_loan.id)

    with pytest.raises(LoanRenewalNotAllowedError):
        renew_loan(db, returned_loan.id)
