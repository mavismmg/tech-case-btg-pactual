def test_create_list_get_update_and_delete_user(client, admin_headers):
    create_response = client.post(
        "/users/",
        json={"name": "Functional User", "email": "functional-user@example.com"},
        headers=admin_headers,
    )
    assert create_response.status_code == 201
    user_id = create_response.json()["id"]

    list_response = client.get("/users/", params={"skip": 0, "limit": 10})
    assert list_response.status_code == 200
    assert list_response.json()["total"] == 1
    assert list_response.json()["items"][0]["id"] == user_id

    get_response = client.get(f"/users/{user_id}")
    assert get_response.status_code == 200
    assert get_response.json()["email"] == "functional-user@example.com"

    update_response = client.put(
        f"/users/{user_id}",
        json={"name": "Updated Functional User"},
        headers=admin_headers,
    )
    assert update_response.status_code == 200
    assert update_response.json()["name"] == "Updated Functional User"

    delete_response = client.delete(f"/users/{user_id}", headers=admin_headers)
    assert delete_response.status_code == 204
    assert client.get(f"/users/{user_id}").status_code == 404


def test_create_user_rejects_invalid_payload_and_duplicate_email(client, admin_headers):
    invalid_response = client.post(
        "/users/",
        json={"name": "", "email": "not-an-email"},
        headers=admin_headers,
    )
    assert invalid_response.status_code == 422

    payload = {"name": "Duplicate User", "email": "duplicate-user@example.com"}
    assert client.post("/users/", json=payload, headers=admin_headers).status_code == 201

    duplicate_response = client.post("/users/", json=payload, headers=admin_headers)
    assert duplicate_response.status_code == 409


def test_get_user_returns_404_for_missing_user(client):
    response = client.get("/users/999")

    assert response.status_code == 404


def test_get_user_loans_returns_empty_page_for_existing_user_without_loans(client, admin_headers):
    create_response = client.post(
        "/users/",
        json={"name": "No Loans User", "email": "no-loans@example.com"},
        headers=admin_headers,
    )
    assert create_response.status_code == 201

    response = client.get(f"/users/{create_response.json()['id']}/loans")

    assert response.status_code == 200
    assert response.json() == {"items": [], "total": 0, "skip": 0, "limit": 100}


def test_get_user_loans_returns_404_for_missing_user(client):
    response = client.get("/users/999/loans")

    assert response.status_code == 404
