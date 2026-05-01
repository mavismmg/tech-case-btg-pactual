from datetime import date, datetime, timedelta, timezone

import app.core.rate_limit as rate_limit_module
from app.models.account import AccountRole
from app.models.loan import Loan
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

    delete_response = client.delete(
        f"/books/{book_response.json()['id']}",
        headers=headers,
    )
    assert delete_response.status_code == 204

    get_deleted_response = client.get(f"/books/{book_response.json()['id']}")
    assert get_deleted_response.status_code == 404


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

    metrics_response = client.get("/metrics/loans", headers=headers)
    assert metrics_response.status_code == 200
    assert metrics_response.json()["total_loans"] == 1
    assert metrics_response.json()["returned_loans"] == 1
    assert metrics_response.json()["events_by_operation"]["loan_created"] == 1
    assert metrics_response.json()["events_by_operation"]["loan_returned"] == 1


def test_loan_metrics_endpoint_is_restricted_to_staff(client, db):
    _bootstrap_admin(client)
    admin_token = _login(client)
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    user_response = client.post(
        "/users/",
        json={"name": "Reader", "email": "reader@example.com"},
        headers=admin_headers,
    )
    assert user_response.status_code == 201

    create_account(
        db,
        AccountCreate(
            name="Reader Account",
            email="reader-account@example.com",
            password="strong-password",
            role=AccountRole.READER,
            user_id=user_response.json()["id"],
        ),
    )
    reader_token = _login(client, "reader-account@example.com")
    reader_headers = {"Authorization": f"Bearer {reader_token}"}

    reader_response = client.get("/metrics/loans", headers=reader_headers)
    assert reader_response.status_code == 403

    admin_response = client.get("/metrics/loans", headers=admin_headers)
    assert admin_response.status_code == 200
    assert admin_response.json()["events_by_operation"] == {}


def test_list_active_and_overdue_loans_endpoints(client, db):
    _bootstrap_admin(client)
    token = _login(client)
    headers = {"Authorization": f"Bearer {token}"}

    user_response = client.post(
        "/users/",
        json={"name": "Reader", "email": "reader@example.com"},
        headers=headers,
    )
    assert user_response.status_code == 201
    user_id = user_response.json()["id"]

    author_response = client.post(
        "/authors/",
        json={"name": "Loan Filter Author"},
        headers=headers,
    )
    assert author_response.status_code == 201
    author_id = author_response.json()["id"]

    active_book_response = client.post(
        "/books/",
        json={
            "isbn": "1234567890",
            "author_id": author_id,
            "title": "Active Loan Book",
            "published_date": "2023-01-01",
        },
        headers=headers,
    )
    assert active_book_response.status_code == 201

    overdue_book_response = client.post(
        "/books/",
        json={
            "isbn": "1234567891",
            "author_id": author_id,
            "title": "Overdue Loan Book",
            "published_date": "2023-01-01",
        },
        headers=headers,
    )
    assert overdue_book_response.status_code == 201

    active_loan_response = client.post(
        "/loans/",
        params={"user_id": user_id, "book_id": active_book_response.json()["id"]},
        headers=headers,
    )
    assert active_loan_response.status_code == 201

    overdue_loan_response = client.post(
        "/loans/",
        params={"user_id": user_id, "book_id": overdue_book_response.json()["id"]},
        headers=headers,
    )
    assert overdue_loan_response.status_code == 201
    overdue_loan_id = overdue_loan_response.json()["id"]

    overdue_loan = db.query(Loan).filter(Loan.id == overdue_loan_id).first()
    assert overdue_loan is not None
    overdue_loan.expected_return_date = datetime.now(timezone.utc) - timedelta(days=1)
    db.commit()

    active_response = client.get("/loans/active?skip=0&limit=100", headers=headers)
    assert active_response.status_code == 200
    assert active_response.json()["total"] == 2

    overdue_response = client.get("/loans/overdue?skip=0&limit=100", headers=headers)
    assert overdue_response.status_code == 200
    assert overdue_response.json()["total"] == 1
    assert overdue_response.json()["items"][0]["id"] == overdue_loan_id

    filtered_response = client.get(f"/loans/?status=active&user_id={user_id}&overdue=true", headers=headers)
    assert filtered_response.status_code == 200
    assert filtered_response.json()["total"] == 1
    assert filtered_response.json()["items"][0]["id"] == overdue_loan_id


def test_health_check_returns_service_status(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] in {"ok", "degraded"}
    assert response.json()["database"] in {"ok", "unavailable"}
    assert response.json()["redis"] in {"ok", "unavailable", "disabled"}


def test_reader_can_request_loan_but_staff_must_approve(client):
    _bootstrap_admin(client)
    admin_token = _login(client)
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    user_response = client.post(
        "/users/",
        json={"name": "Reader", "email": "reader@example.com"},
        headers=admin_headers,
    )
    assert user_response.status_code == 201

    reader_account_response = client.post(
        "/accounts/",
        json={
            "name": "Reader Account",
            "email": "reader-account@example.com",
            "password": "strong-password",
            "role": "reader",
            "user_id": user_response.json()["id"],
        },
        headers=admin_headers,
    )
    assert reader_account_response.status_code == 201
    assert reader_account_response.json()["user_id"] == user_response.json()["id"]

    reader_token = _login(client, "reader-account@example.com")
    reader_headers = {"Authorization": f"Bearer {reader_token}"}

    author_response = client.post(
        "/authors/",
        json={"name": "Request Author"},
        headers=admin_headers,
    )
    assert author_response.status_code == 201

    book_response = client.post(
        "/books/",
        json={
            "isbn": "1234567890",
            "author_id": author_response.json()["id"],
            "title": "Request Book",
            "published_date": "2023-01-01",
        },
        headers=admin_headers,
    )
    assert book_response.status_code == 201

    direct_loan_response = client.post(
        "/loans/",
        params={
            "user_id": user_response.json()["id"],
            "book_id": book_response.json()["id"],
        },
        headers=reader_headers,
    )
    assert direct_loan_response.status_code == 403

    request_response = client.post(
        "/loan-requests/",
        json={"book_id": book_response.json()["id"]},
        headers=reader_headers,
    )
    assert request_response.status_code == 201
    assert request_response.json()["status"] == "pending"

    reader_approve_response = client.post(
        f"/loan-requests/{request_response.json()['id']}/approve",
        headers=reader_headers,
    )
    assert reader_approve_response.status_code == 403

    approve_response = client.post(
        f"/loan-requests/{request_response.json()['id']}/approve",
        headers=admin_headers,
    )
    assert approve_response.status_code == 200
    assert approve_response.json()["status"] == "approved"

    loans_response = client.get(f"/users/{user_response.json()['id']}/loans", headers=admin_headers)
    assert loans_response.status_code == 200
    assert loans_response.json()["total"] == 1
    assert loans_response.json()["items"][0]["status"] == "active"


def test_loan_request_rate_limit_returns_429(client, monkeypatch):
    _bootstrap_admin(client)
    admin_token = _login(client)
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    user_response = client.post(
        "/users/",
        json={"name": "Reader", "email": "reader@example.com"},
        headers=admin_headers,
    )
    assert user_response.status_code == 201

    reader_account_response = client.post(
        "/accounts/",
        json={
            "name": "Reader Account",
            "email": "reader-account@example.com",
            "password": "strong-password",
            "role": "reader",
            "user_id": user_response.json()["id"],
        },
        headers=admin_headers,
    )
    assert reader_account_response.status_code == 201

    reader_token = _login(client, "reader-account@example.com")
    reader_headers = {"Authorization": f"Bearer {reader_token}"}

    fake_redis = FakeRedis()
    monkeypatch.setattr(rate_limit_module, "RATE_LIMIT_ENABLED", True)
    monkeypatch.setattr(rate_limit_module, "get_redis_client", lambda: fake_redis)

    for _ in range(10):
        response = client.post("/loan-requests/", json={"book_id": 999}, headers=reader_headers)
        assert response.status_code == 404

    blocked_response = client.post("/loan-requests/", json={"book_id": 999}, headers=reader_headers)

    assert blocked_response.status_code == 429
    assert blocked_response.headers["Retry-After"] == "60"


def test_account_creation_rate_limit_returns_429(client, monkeypatch):
    _bootstrap_admin(client)
    admin_token = _login(client)
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    fake_redis = FakeRedis()
    monkeypatch.setattr(rate_limit_module, "RATE_LIMIT_ENABLED", True)
    monkeypatch.setattr(rate_limit_module, "get_redis_client", lambda: fake_redis)

    for _ in range(10):
        response = client.post(
            "/accounts/",
            json={
                "name": "Librarian",
                "email": "librarian@example.com",
                "password": "strong-password",
                "role": "librarian",
            },
            headers=admin_headers,
        )
        assert response.status_code in {201, 409}

    blocked_response = client.post(
        "/accounts/",
        json={
            "name": "Librarian",
            "email": "librarian@example.com",
            "password": "strong-password",
            "role": "librarian",
        },
        headers=admin_headers,
    )

    assert blocked_response.status_code == 429
    assert blocked_response.headers["Retry-After"] == "60"


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
