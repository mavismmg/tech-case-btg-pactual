import pytest

from app.services.loan_service import (
    LoanAlreadyReturnedError,
    LoanBookIsNotAvailableError,
    LoanLimitExceededError,
    LoanUserNotFoundError,
    create_loan,
    return_loan,
)
from app.services.user_service import UserAlreadyExistsError, delete_user


def test_user_cannot_exceed_three_active_loans(db, user_factory, book_factory):
    user = user_factory()
    for _ in range(3):
        create_loan(db, user.id, book_factory().id)

    with pytest.raises(LoanLimitExceededError):
        create_loan(db, user.id, book_factory().id)


def test_same_book_cannot_have_two_active_loans(db, user_factory, book_factory):
    book = book_factory()
    create_loan(db, user_factory().id, book.id)

    with pytest.raises(LoanBookIsNotAvailableError):
        create_loan(db, user_factory().id, book.id)


def test_duplicate_return_does_not_recalculate_or_change_fine(db, active_loan_factory):
    loan = active_loan_factory()
    returned_loan = return_loan(db, loan.id)
    original_fine = returned_loan.fine_value
    original_return_date = returned_loan.actual_return_date

    with pytest.raises(LoanAlreadyReturnedError):
        return_loan(db, loan.id)

    db.refresh(loan)
    assert loan.fine_value == original_fine
    assert loan.actual_return_date == original_return_date


def test_deleted_user_cannot_create_new_loan(db, user_factory, book_factory):
    user = user_factory()
    delete_user(db, user.id)

    with pytest.raises(LoanUserNotFoundError):
        create_loan(db, user.id, book_factory().id)


def test_duplicate_user_email_is_blocked(db, user_factory):
    user_factory(email="duplicate-regression@example.com")

    with pytest.raises(UserAlreadyExistsError):
        user_factory(email="duplicate-regression@example.com")


def test_user_loans_endpoint_returns_404_for_missing_user(client):
    response = client.get("/users/999/loans")

    assert response.status_code == 404


def test_pagination_contract_and_invalid_values(client, user_factory):
    user_factory()
    response = client.get("/users/", params={"skip": 0, "limit": 1})

    assert response.status_code == 200
    assert set(response.json()) == {"items", "total", "skip", "limit"}
    assert response.json()["skip"] == 0
    assert response.json()["limit"] == 1

    assert client.get("/users/", params={"skip": -1}).status_code == 422
    assert client.get("/users/", params={"limit": 0}).status_code == 422
    assert client.get("/users/", params={"limit": 101}).status_code == 422


def test_book_availability_endpoints_continue_grouping_exemplars_by_isbn(client, admin_headers):
    author_response = client.post("/authors/", json={"name": "Grouped ISBN Author"}, headers=admin_headers)
    assert author_response.status_code == 201

    payload = {
        "isbn": "1234567890",
        "author_id": author_response.json()["id"],
        "title": "Grouped ISBN Book",
        "published_date": "2023-01-01",
    }
    first_response = client.post("/books/", json=payload, headers=admin_headers)
    second_response = client.post("/books/", json=payload, headers=admin_headers)
    assert first_response.status_code == 201
    assert second_response.status_code == 201

    count_response = client.get("/books/count/1234567890")
    assert count_response.status_code == 200
    assert count_response.json()["available_exemplars"] == 2

    exemplars_response = client.get("/books/exemplars/1234567890")
    assert exemplars_response.status_code == 200
    assert {book["id"] for book in exemplars_response.json()} == {
        first_response.json()["id"],
        second_response.json()["id"],
    }
