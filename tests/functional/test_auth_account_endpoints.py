from app.models.account import AccountRole


def test_bootstrap_login_me_and_bootstrap_reuse(client):
    bootstrap_response = client.post(
        "/auth/bootstrap",
        json={"name": "Admin", "email": "admin@example.com", "password": "strong-password"},
    )
    assert bootstrap_response.status_code == 201

    login_response = client.post(
        "/auth/login",
        json={"email": "admin@example.com", "password": "strong-password"},
    )
    assert login_response.status_code == 200
    login_body = login_response.json()
    token = login_body["access_token"]
    assert set(login_body["account"].keys()) == {"id", "name", "email", "role"}

    me_response = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me_response.status_code == 200
    assert me_response.json()["email"] == "admin@example.com"

    second_bootstrap_response = client.post(
        "/auth/bootstrap",
        json={"name": "Other Admin", "email": "other-admin@example.com", "password": "strong-password"},
    )
    assert second_bootstrap_response.status_code == 409


def test_login_invalid_credentials_and_missing_token_are_rejected(client, admin_headers):
    invalid_login_response = client.post(
        "/auth/login",
        json={"email": "admin@example.com", "password": "wrong-password"},
    )
    assert invalid_login_response.status_code == 401

    missing_token_response = client.get("/auth/me")
    assert missing_token_response.status_code == 401

    invalid_token_response = client.get("/auth/me", headers={"Authorization": "Bearer invalid-token"})
    assert invalid_token_response.status_code == 401


def test_admin_can_create_list_and_deactivate_account(client, admin_headers, user_factory):
    response = client.post(
        "/accounts/",
        json={
            "name": "Reader Account",
            "email": "reader-account@example.com",
            "password": "strong-password",
            "role": "reader",
            "user_id": user_factory().id,
        },
        headers=admin_headers,
    )
    assert response.status_code == 201
    account_id = response.json()["id"]

    list_response = client.get("/accounts/", headers=admin_headers)
    assert list_response.status_code == 200
    assert list_response.json()["total"] == 2

    deactivate_response = client.delete(f"/accounts/{account_id}", headers=admin_headers)
    assert deactivate_response.status_code == 204

    inactive_login_response = client.post(
        "/auth/login",
        json={"email": "reader-account@example.com", "password": "strong-password"},
    )
    assert inactive_login_response.status_code == 401


def test_account_creation_role_invariants(client, admin_headers, user_factory):
    reader_without_user_response = client.post(
        "/accounts/",
        json={
            "name": "Invalid Reader",
            "email": "invalid-reader@example.com",
            "password": "strong-password",
            "role": "reader",
        },
        headers=admin_headers,
    )
    assert reader_without_user_response.status_code == 422

    staff_with_user_response = client.post(
        "/accounts/",
        json={
            "name": "Invalid Staff",
            "email": "invalid-staff@example.com",
            "password": "strong-password",
            "role": "librarian",
            "user_id": user_factory().id,
        },
        headers=admin_headers,
    )
    assert staff_with_user_response.status_code == 422


def test_reader_and_librarian_permissions_are_restricted(client, account_factory, reader_headers, librarian_headers):
    reader_user_create_response = client.post(
        "/users/",
        json={"name": "Forbidden", "email": "forbidden@example.com"},
        headers=reader_headers,
    )
    assert reader_user_create_response.status_code == 403

    librarian_account_list_response = client.get("/accounts/", headers=librarian_headers)
    assert librarian_account_list_response.status_code == 403

    admin_only_account = account_factory(role=AccountRole.ADMIN)
    assert admin_only_account.role == AccountRole.ADMIN.value
