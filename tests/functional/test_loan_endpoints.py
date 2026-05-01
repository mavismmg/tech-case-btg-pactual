from datetime import datetime, timedelta


def test_create_loan_endpoint_sets_status_due_date_and_book_availability(
    client,
    db,
    admin_headers,
    user_factory,
    book_factory,
):
    user = user_factory()
    book = book_factory()

    response = client.post("/loans/", params={"user_id": user.id, "book_id": book.id}, headers=admin_headers)

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "active"
    loan_date = datetime.fromisoformat(body["loan_date"].replace("Z", "+00:00"))
    expected_return_date = datetime.fromisoformat(body["expected_return_date"].replace("Z", "+00:00"))
    assert abs((expected_return_date - loan_date) - timedelta(days=14)) < timedelta(seconds=1)
    db.refresh(book)
    assert book.is_available is False


def test_create_loan_endpoint_rejects_missing_user_missing_book_and_unavailable_book(
    client,
    admin_headers,
    user_factory,
    book_factory,
):
    user = user_factory()
    book = book_factory()

    missing_user_response = client.post("/loans/", params={"user_id": 999, "book_id": book.id}, headers=admin_headers)
    assert missing_user_response.status_code == 404

    missing_book_response = client.post("/loans/", params={"user_id": user.id, "book_id": 999}, headers=admin_headers)
    assert missing_book_response.status_code == 404

    loan_response = client.post(
        "/loans/",
        params={"user_id": user.id, "book_id": book.id},
        headers=admin_headers,
    )
    assert loan_response.status_code == 201

    unavailable_response = client.post(
        "/loans/",
        params={"user_id": user_factory().id, "book_id": book.id},
        headers=admin_headers,
    )
    assert unavailable_response.status_code == 409


def test_create_loan_endpoint_rejects_fourth_active_loan(client, admin_headers, user_factory, book_factory):
    user = user_factory()
    for _ in range(3):
        assert (
            client.post(
                "/loans/",
                params={"user_id": user.id, "book_id": book_factory().id},
                headers=admin_headers,
            ).status_code
            == 201
        )

    response = client.post("/loans/", params={"user_id": user.id, "book_id": book_factory().id}, headers=admin_headers)

    assert response.status_code == 409


def test_return_loan_endpoint_inside_due_date_and_duplicate_return(
    client,
    db,
    admin_headers,
    active_loan_factory,
):
    loan = active_loan_factory()

    response = client.put(f"/loans/{loan.id}/return", headers=admin_headers)

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "returned"
    assert body["actual_return_date"] is not None
    assert body["fine_value"] == 0.0
    db.refresh(loan.book)
    assert loan.book.is_available is True

    duplicate_response = client.put(f"/loans/{loan.id}/return", headers=admin_headers)
    assert duplicate_response.status_code == 409


def test_return_loan_endpoint_calculates_overdue_fine(client, admin_headers, overdue_loan_factory):
    loan = overdue_loan_factory(days_overdue=3)

    response = client.put(f"/loans/{loan.id}/return", headers=admin_headers)

    assert response.status_code == 200
    assert response.json()["fine_value"] >= 6.0


def test_list_active_overdue_and_user_history(client, admin_headers, active_loan_factory, overdue_loan_factory):
    active_loan = active_loan_factory()
    overdue_loan = overdue_loan_factory(user=active_loan.user)

    active_response = client.get("/loans/active", headers=admin_headers)
    assert active_response.status_code == 200
    assert active_response.json()["total"] == 2

    overdue_response = client.get("/loans/overdue", headers=admin_headers)
    assert overdue_response.status_code == 200
    assert overdue_response.json()["total"] == 1
    assert overdue_response.json()["items"][0]["id"] == overdue_loan.id

    history_response = client.get(f"/users/{active_loan.user_id}/loans", headers=admin_headers)
    assert history_response.status_code == 200
    assert history_response.json()["total"] == 2


def test_list_loans_overdue_false_excludes_active_overdue_loans(client, overdue_loan_factory, active_loan_factory):
    overdue_loan = overdue_loan_factory()
    active_loan = active_loan_factory()

    response = client.get("/loans/", params={"overdue": False})

    assert response.status_code == 200
    ids = {loan["id"] for loan in response.json()["items"]}
    assert active_loan.id in ids
    assert overdue_loan.id not in ids
