from datetime import datetime, timedelta, timezone

from app.services import notification_service


def test_admin_sends_due_loan_notifications_by_email(client, admin_headers, loan_factory):
    now = datetime.now(timezone.utc)
    loan = loan_factory(expected_return_date=now + timedelta(hours=12))

    response = client.post(
        "/notifications/due-loans/send",
        params={"days_ahead": 1, "channel": "email"},
        headers=admin_headers,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["total_due_loans"] == 1
    assert body["sent_email_count"] == 1
    assert body["loans"][0]["loan_id"] == loan.id
    assert body["deliveries"][0]["channel"] == "email"
    assert body["deliveries"][0]["to"] == loan.user.email


def test_librarian_sends_due_loan_webhook_notification(
    client,
    librarian_headers,
    loan_factory,
    monkeypatch,
):
    loan = loan_factory(expected_return_date=datetime.now(timezone.utc) + timedelta(hours=4))
    calls = []

    class FakeResponse:
        def raise_for_status(self):
            return None

    def fake_post(url, json, timeout):
        calls.append({"url": url, "json": json, "timeout": timeout})
        return FakeResponse()

    monkeypatch.setenv("DUE_LOAN_WEBHOOK_URL", "https://example.com/library-webhook")
    monkeypatch.setattr(notification_service.httpx, "post", fake_post)

    response = client.post(
        "/notifications/due-loans/send",
        params={"days_ahead": 1, "channel": "webhook"},
        headers=librarian_headers,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["sent_webhook_count"] == 1
    assert body["failed_count"] == 0
    assert calls[0]["url"] == "https://example.com/library-webhook"
    assert calls[0]["json"]["loans"][0]["loan_id"] == loan.id


def test_due_loan_notifications_are_restricted_to_staff(client, reader_headers):
    missing_token_response = client.post("/notifications/due-loans/send")
    assert missing_token_response.status_code == 401

    reader_response = client.post("/notifications/due-loans/send", headers=reader_headers)
    assert reader_response.status_code == 403


def test_due_loan_notification_endpoint_validates_query_params(client, admin_headers):
    invalid_days_response = client.post(
        "/notifications/due-loans/send",
        params={"days_ahead": 31},
        headers=admin_headers,
    )
    invalid_channel_response = client.post(
        "/notifications/due-loans/send",
        params={"channel": "sms"},
        headers=admin_headers,
    )

    assert invalid_days_response.status_code == 422
    assert invalid_channel_response.status_code == 422


def test_due_loan_notification_endpoint_returns_empty_result_when_no_due_loans(client, admin_headers):
    response = client.post(
        "/notifications/due-loans/send",
        params={"channel": "email"},
        headers=admin_headers,
    )

    assert response.status_code == 200
    assert response.json()["total_due_loans"] == 0
    assert response.json()["deliveries"] == []


def test_webhook_channel_without_url_returns_controlled_failure(
    client,
    admin_headers,
    loan_factory,
    monkeypatch,
):
    monkeypatch.delenv("DUE_LOAN_WEBHOOK_URL", raising=False)
    loan = loan_factory(expected_return_date=datetime.now(timezone.utc) + timedelta(hours=5))

    response = client.post(
        "/notifications/due-loans/send",
        params={"days_ahead": 1, "channel": "webhook"},
        headers=admin_headers,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["sent_webhook_count"] == 0
    assert body["failed_count"] == 1
    assert body["deliveries"][0]["loan_id"] == loan.id
    assert body["deliveries"][0]["status"] == "failed"
    assert body["deliveries"][0]["error_message"] == "DUE_LOAN_WEBHOOK_URL is not configured."
