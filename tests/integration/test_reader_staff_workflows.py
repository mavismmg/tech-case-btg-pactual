from app.models.account import AccountRole


def _login(client, email: str, password: str = "strong-password") -> str:
    response = client.post("/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200
    return response.json()["access_token"]


def test_reader_loan_request_approval_creates_active_loan_and_metrics(
    client,
    admin_headers,
    account_factory,
    book_factory,
):
    reader_account = account_factory(role=AccountRole.READER)
    reader_headers = {"Authorization": f"Bearer {_login(client, reader_account.email)}"}
    book = book_factory()

    request_response = client.post("/loan-requests/", json={"book_id": book.id}, headers=reader_headers)
    assert request_response.status_code == 201
    assert request_response.json()["status"] == "pending"

    approve_response = client.post(
        f"/loan-requests/{request_response.json()['id']}/approve",
        headers=admin_headers,
    )
    assert approve_response.status_code == 200
    assert approve_response.json()["status"] == "approved"

    history_response = client.get(f"/users/{reader_account.user_id}/loans", headers=admin_headers)
    assert history_response.status_code == 200
    assert history_response.json()["total"] == 1
    assert history_response.json()["items"][0]["status"] == "active"
    assert history_response.json()["items"][0]["book_id"] == book.id

    metrics_response = client.get("/metrics/loans", headers=admin_headers)
    assert metrics_response.status_code == 200
    assert metrics_response.json()["total_loans"] == 1
    assert metrics_response.json()["events_by_operation"]["loan_request_created"] == 1
    assert metrics_response.json()["events_by_operation"]["loan_request_approved"] == 1
    assert metrics_response.json()["events_by_operation"]["loan_created"] == 1


def test_reader_return_request_approval_returns_loan(
    client,
    admin_headers,
    account_factory,
    active_loan_factory,
):
    reader_account = account_factory(role=AccountRole.READER)
    reader_headers = {"Authorization": f"Bearer {_login(client, reader_account.email)}"}
    loan = active_loan_factory(user_id=reader_account.user_id)

    request_response = client.post("/return-requests/", json={"loan_id": loan.id}, headers=reader_headers)
    assert request_response.status_code == 201

    approve_response = client.post(
        f"/loan-requests/{request_response.json()['id']}/approve",
        headers=admin_headers,
    )
    assert approve_response.status_code == 200
    assert approve_response.json()["status"] == "approved"

    loan_response = client.get(f"/loans/{loan.id}", headers=admin_headers)
    assert loan_response.status_code == 200
    assert loan_response.json()["status"] == "returned"


def test_reader_renewal_request_approval_extends_due_date_once(
    client,
    admin_headers,
    account_factory,
    active_loan_factory,
):
    reader_account = account_factory(role=AccountRole.READER)
    reader_headers = {"Authorization": f"Bearer {_login(client, reader_account.email)}"}
    loan = active_loan_factory(user_id=reader_account.user_id)
    original_due_date = loan.expected_return_date

    request_response = client.post("/renewal-requests/", json={"loan_id": loan.id}, headers=reader_headers)
    assert request_response.status_code == 201

    approve_response = client.post(
        f"/loan-requests/{request_response.json()['id']}/approve",
        headers=admin_headers,
    )
    assert approve_response.status_code == 200

    loan_response = client.get(f"/loans/{loan.id}", headers=admin_headers)
    assert loan_response.status_code == 200
    assert loan_response.json()["renewal_count"] == 1
    assert loan_response.json()["expected_return_date"] != original_due_date.isoformat().replace("+00:00", "Z")


def test_health_and_metrics_endpoints_are_available(client, admin_headers):
    health_response = client.get("/health")
    assert health_response.status_code == 200
    assert health_response.json()["database"] in {"ok", "unavailable"}
    assert health_response.json()["redis"] in {"ok", "unavailable", "disabled"}

    metrics_response = client.get("/metrics/loans", headers=admin_headers)
    assert metrics_response.status_code == 200
    assert metrics_response.json()["events_by_operation"] == {}
