import csv
from io import StringIO

from app.models.account import AccountRole


CSV_FIELDS = [
    "id",
    "operation",
    "loan_id",
    "loan_request_id",
    "user_id",
    "book_id",
    "account_id",
    "reviewer_account_id",
    "fine_value",
    "created_at",
]


def _csv_rows(content: str) -> list[dict[str, str]]:
    return list(csv.DictReader(StringIO(content)))


def _login(client, email: str, password: str = "strong-password") -> str:
    response = client.post("/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200
    return response.json()["access_token"]


def test_admin_exports_empty_loan_operation_metrics_csv(client, admin_headers):
    response = client.get("/metrics/loans/export.csv", headers=admin_headers)

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    assert response.headers["content-disposition"] == "attachment; filename=loan_operation_metrics.csv"
    assert response.text == ",".join(CSV_FIELDS) + "\r\n"


def test_librarian_can_export_loan_operation_metrics_csv(client, account_factory):
    librarian = account_factory(role=AccountRole.LIBRARIAN)
    token = _login(client, librarian.email)

    response = client.get("/metrics/loans/export.csv", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    assert response.text == ",".join(CSV_FIELDS) + "\r\n"


def test_loan_operation_metrics_csv_export_is_restricted_to_staff(client, reader_headers):
    missing_token_response = client.get("/metrics/loans/export.csv")
    assert missing_token_response.status_code == 401

    reader_response = client.get("/metrics/loans/export.csv", headers=reader_headers)
    assert reader_response.status_code == 403


def test_loan_operation_metrics_csv_contains_created_and_returned_events(
    client,
    db,
    admin_headers,
    user_factory,
    book_factory,
):
    user = user_factory()
    book = book_factory()
    loan_response = client.post(
        "/loans/",
        params={"user_id": user.id, "book_id": book.id},
        headers=admin_headers,
    )
    assert loan_response.status_code == 201

    return_response = client.put(f"/loans/{loan_response.json()['id']}/return", headers=admin_headers)
    assert return_response.status_code == 200

    response = client.get("/metrics/loans/export.csv", headers=admin_headers)

    assert response.status_code == 200
    rows = _csv_rows(response.text)
    assert [row["operation"] for row in rows] == ["loan_created", "loan_returned"]
    assert rows[0]["loan_id"] == str(loan_response.json()["id"])
    assert rows[0]["loan_request_id"] == ""
    assert rows[0]["account_id"] == ""
    assert rows[0]["reviewer_account_id"] == ""
    assert rows[0]["fine_value"] == ""
    assert rows[1]["fine_value"] == "0.0"
    assert rows[1]["created_at"].endswith("Z")


def test_loan_operation_metrics_csv_exports_overdue_return_fine(
    client,
    admin_headers,
    overdue_loan_factory,
):
    loan = overdue_loan_factory(days_overdue=2)
    return_response = client.put(f"/loans/{loan.id}/return", headers=admin_headers)
    assert return_response.status_code == 200

    response = client.get("/metrics/loans/export.csv", headers=admin_headers)

    rows = _csv_rows(response.text)
    returned_row = next(row for row in rows if row["operation"] == "loan_returned")
    assert float(returned_row["fine_value"]) >= 4.0
