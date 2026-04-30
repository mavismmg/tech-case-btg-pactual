from datetime import date

import app.core.rate_limit as rate_limit_module
from app.models.account import AccountRole
from app.schemas.account import AccountCreate
from app.services.account_service import create_account


class FakeRedis:
    def __init__(self):
        self.values = {}
        self.ttls = {}

    def incr(self, key):
        self.values[key] = self.values.get(key, 0) + 1
        return self.values[key]

    def expire(self, key, window_seconds):
        self.ttls[key] = window_seconds

    def ttl(self, key):
        return self.ttls.get(key, -1)


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
    return response.json()


def _login(client, email="admin@example.com", password="strong-password") -> str:
    response = client.post(
        "/auth/login",
        json={
            "email": email,
            "password": password,
        },
    )
    assert response.status_code == 200
    return response.json()["access_token"]


def test_protected_book_creation_requires_token(client):
    response = client.post(
        "/books/",
        json={
            "isbn": "1234567890",
            "author_id": 1,
            "title": "Protected Book",
            "published_date": "2023-01-01",
        },
    )

    assert response.status_code == 401


def test_librarian_can_create_author_and_book(client, db):
    _bootstrap_admin(client)
    create_account(
        db,
        AccountCreate(
            name="Librarian",
            email="librarian@example.com",
            password="strong-password",
            role=AccountRole.LIBRARIAN,
        ),
    )
    token = _login(client, "librarian@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    author_response = client.post(
        "/authors/",
        json={"name": "Test Author"},
        headers=headers,
    )
    assert author_response.status_code == 201

    book_response = client.post(
        "/books/",
        json={
            "isbn": "1234567890",
            "author_id": author_response.json()["id"],
            "title": "Test Book",
            "published_date": date(2023, 1, 1).isoformat(),
        },
        headers=headers,
    )

    assert book_response.status_code == 201
    assert book_response.json()["title"] == "Test Book"


def test_auth_flow_create_and_return_loan(client):
    _bootstrap_admin(client)
    token = _login(client)
    headers = {"Authorization": f"Bearer {token}"}

    user_response = client.post(
        "/users/",
        json={"name": "Reader", "email": "reader@example.com"},
        headers=headers,
    )
    assert user_response.status_code == 201

    author_response = client.post(
        "/authors/",
        json={"name": "Loan Author"},
        headers=headers,
    )
    assert author_response.status_code == 201

    book_response = client.post(
        "/books/",
        json={
            "isbn": "1234567890",
            "author_id": author_response.json()["id"],
            "title": "Loan Book",
            "published_date": "2023-01-01",
        },
        headers=headers,
    )
    assert book_response.status_code == 201

    loan_response = client.post(
        "/loans/",
        params={
            "user_id": user_response.json()["id"],
            "book_id": book_response.json()["id"],
        },
        headers=headers,
    )
    assert loan_response.status_code == 201
    assert loan_response.json()["status"] == "active"

    return_response = client.put(
        f"/loans/{loan_response.json()['id']}/return",
        headers=headers,
    )
    assert return_response.status_code == 200
    assert return_response.json()["status"] == "returned"


def test_login_invalid_credentials_returns_401(client):
    _bootstrap_admin(client)

    response = client.post(
        "/auth/login",
        json={
            "email": "admin@example.com",
            "password": "wrong-password",
        },
    )

    assert response.status_code == 401


def test_login_rate_limit_returns_429(client, monkeypatch):
    _bootstrap_admin(client)
    fake_redis = FakeRedis()
    monkeypatch.setattr(rate_limit_module, "RATE_LIMIT_ENABLED", True)
    monkeypatch.setattr(rate_limit_module, "get_redis_client", lambda: fake_redis)

    for _ in range(10):
        response = client.post(
            "/auth/login",
            json={
                "email": "admin@example.com",
                "password": "strong-password",
            },
        )
        assert response.status_code == 200

    blocked_response = client.post(
        "/auth/login",
        json={
            "email": "admin@example.com",
            "password": "strong-password",
        },
    )

    assert blocked_response.status_code == 429
    assert blocked_response.headers["Retry-After"] == "60"
