from datetime import date

from app.models.account import AccountRole
from app.schemas.account import AccountCreate
from app.services.account_service import create_account


def _bootstrap_admin(client):
    response = client.post(
        "/auth/bootstrap",
        json={
            "name": "Admin",
            "email": "admin@example.com",
            "password": "strong-password",
        },
    )
    assert response.status_code == 201


def _login(client, email="admin@example.com") -> str:
    response = client.post(
        "/auth/login",
        json={
            "email": email,
            "password": "strong-password",
        },
    )
    assert response.status_code == 200
    return response.json()["access_token"]


def _admin_headers(client) -> dict[str, str]:
    _bootstrap_admin(client)
    token = _login(client)
    return {"Authorization": f"Bearer {token}"}


def _create_author(client, headers) -> int:
    response = client.post("/authors/", json={"name": "Validation Author"}, headers=headers)
    assert response.status_code == 201
    return response.json()["id"]


def _create_user(client, headers) -> int:
    response = client.post(
        "/users/",
        json={"name": "Validation Reader", "email": "validation-reader@example.com"},
        headers=headers,
    )
    assert response.status_code == 201
    return response.json()["id"]


def _create_book(client, headers, author_id: int, isbn: str = "1234567890") -> int:
    response = client.post(
        "/books/",
        json={
            "isbn": isbn,
            "author_id": author_id,
            "title": "Validation Book",
            "published_date": date(2023, 1, 1).isoformat(),
        },
        headers=headers,
    )
    assert response.status_code == 201
    return response.json()["id"]


def test_paginated_endpoints_reject_invalid_skip_and_limit(client):
    headers = _admin_headers(client)

    endpoints = [
        "/authors/",
        "/books/",
        "/users/",
        "/loans/",
        "/loans/active",
        "/loans/overdue",
        "/accounts/",
        "/loan-requests/",
    ]

    for endpoint in endpoints:
        request_headers = headers if endpoint in {"/accounts/", "/loan-requests/"} else None
        assert client.get(endpoint, params={"skip": -1}, headers=request_headers).status_code == 422
        assert client.get(endpoint, params={"limit": 0}, headers=request_headers).status_code == 422
        assert client.get(endpoint, params={"limit": -1}, headers=request_headers).status_code == 422
        assert client.get(endpoint, params={"limit": 101}, headers=request_headers).status_code == 422


def test_path_and_query_ids_reject_non_positive_values(client):
    headers = _admin_headers(client)

    for endpoint in ["/users/0", "/users/-1", "/books/0", "/books/-1", "/authors/0", "/authors/-1", "/loans/0"]:
        assert client.get(endpoint).status_code == 422

    assert client.get("/users/not-an-id").status_code == 422
    assert client.get("/books/not-an-id").status_code == 422
    assert client.get("/authors/not-an-id").status_code == 422
    assert client.get("/loans/not-an-id").status_code == 422

    assert client.get("/users/0/loans").status_code == 422
    assert client.get("/users/-1/loans").status_code == 422
    assert client.get("/loans/", params={"user_id": -1}).status_code == 422
    assert client.post("/loans/", params={"user_id": 0, "book_id": 1}, headers=headers).status_code == 422
    assert client.post("/loans/", params={"user_id": 1, "book_id": -1}, headers=headers).status_code == 422
    assert client.put("/loans/0/return", headers=headers).status_code == 422
    assert client.delete("/accounts/0", headers=headers).status_code == 422
    assert client.post("/loan-requests/0/approve", headers=headers).status_code == 422
    assert client.post("/loan-requests/-1/reject", json={"reason": "invalid id"}, headers=headers).status_code == 422


def test_book_isbn_path_validation_and_not_found_semantics(client):
    headers = _admin_headers(client)

    invalid_isbns = ["123456789", "12345678901234", "12345abcde", "-1234567890"]
    for isbn in invalid_isbns:
        assert client.get(f"/books/count/{isbn}").status_code == 422
        assert client.get(f"/books/exemplars/{isbn}").status_code == 422

    missing_isbn = "9788520943489"
    assert client.get(f"/books/count/{missing_isbn}").status_code == 404
    assert client.get(f"/books/exemplars/{missing_isbn}").status_code == 404

    author_id = _create_author(client, headers)
    user_id = _create_user(client, headers)
    book_id = _create_book(client, headers, author_id, isbn=missing_isbn)

    loan_response = client.post("/loans/", params={"user_id": user_id, "book_id": book_id}, headers=headers)
    assert loan_response.status_code == 201

    count_response = client.get(f"/books/count/{missing_isbn}")
    assert count_response.status_code == 200
    assert count_response.json()["available_exemplars"] == 0
    assert count_response.json()["is_available"] is False

    exemplars_response = client.get(f"/books/exemplars/{missing_isbn}")
    assert exemplars_response.status_code == 200
    assert exemplars_response.json() == []


def test_reader_can_create_pending_loan_request_for_existing_book(client, db):
    admin_headers = _admin_headers(client)
    user_id = _create_user(client, admin_headers)
    author_id = _create_author(client, admin_headers)
    book_id = _create_book(client, admin_headers, author_id)

    create_account(
        db,
        AccountCreate(
            name="Reader Account",
            email="reader-account@example.com",
            password="strong-password",
            role=AccountRole.READER,
            user_id=user_id,
        ),
    )
    reader_token = _login(client, "reader-account@example.com")
    reader_headers = {"Authorization": f"Bearer {reader_token}"}

    response = client.post("/loan-requests/", json={"book_id": book_id}, headers=reader_headers)

    assert response.status_code == 201
    assert response.json()["status"] == "pending"
