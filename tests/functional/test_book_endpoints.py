from datetime import date


def test_create_list_get_and_delete_book(client, admin_headers):
    author_response = client.post("/authors/", json={"name": "Functional Author"}, headers=admin_headers)
    assert author_response.status_code == 201

    book_response = client.post(
        "/books/",
        json={
            "isbn": "1234567890",
            "author_id": author_response.json()["id"],
            "title": "Functional Book",
            "published_date": date(2023, 1, 1).isoformat(),
        },
        headers=admin_headers,
    )
    assert book_response.status_code == 201
    book_id = book_response.json()["id"]

    list_response = client.get("/books/", params={"skip": 0, "limit": 10})
    assert list_response.status_code == 200
    assert list_response.json()["total"] == 1

    get_response = client.get(f"/books/{book_id}")
    assert get_response.status_code == 200
    assert get_response.json()["title"] == "Functional Book"

    delete_response = client.delete(f"/books/{book_id}", headers=admin_headers)
    assert delete_response.status_code == 204
    assert client.get(f"/books/{book_id}").status_code == 404


def test_book_creation_rejects_invalid_payload_author_and_future_date(client, admin_headers):
    invalid_payload_response = client.post(
        "/books/",
        json={"isbn": "abc", "author_id": 0, "title": "", "published_date": "2999-01-01"},
        headers=admin_headers,
    )
    assert invalid_payload_response.status_code == 422

    missing_author_response = client.post(
        "/books/",
        json={
            "isbn": "1234567890",
            "author_id": 999,
            "title": "Missing Author Book",
            "published_date": "2023-01-01",
        },
        headers=admin_headers,
    )
    assert missing_author_response.status_code == 404


def test_book_creation_rejects_same_title_and_author_with_different_isbn(client, admin_headers):
    author_response = client.post("/authors/", json={"name": "Conflict API Author"}, headers=admin_headers)
    assert author_response.status_code == 201
    author_id = author_response.json()["id"]

    payload = {
        "isbn": "1234567890",
        "author_id": author_id,
        "title": "Conflicting API Book",
        "published_date": "2023-01-01",
    }
    assert client.post("/books/", json=payload, headers=admin_headers).status_code == 201

    conflict_payload = {**payload, "isbn": "1234567891"}
    conflict_response = client.post("/books/", json=conflict_payload, headers=admin_headers)

    assert conflict_response.status_code == 409
    assert conflict_response.json()["detail"] == "Book title already exists for this author with a different ISBN."


def test_book_creation_allows_same_title_author_and_isbn_as_new_exemplar(client, admin_headers):
    author_response = client.post("/authors/", json={"name": "Exemplar API Author"}, headers=admin_headers)
    assert author_response.status_code == 201

    payload = {
        "isbn": "1234567890",
        "author_id": author_response.json()["id"],
        "title": "Same Exemplar API Book",
        "published_date": "2023-01-01",
    }

    first_response = client.post("/books/", json=payload, headers=admin_headers)
    second_response = client.post("/books/", json=payload, headers=admin_headers)

    assert first_response.status_code == 201
    assert second_response.status_code == 201
    assert first_response.json()["id"] != second_response.json()["id"]


def test_book_creation_allows_same_title_for_different_authors(client, admin_headers):
    first_author_response = client.post("/authors/", json={"name": "First Title API Author"}, headers=admin_headers)
    second_author_response = client.post("/authors/", json={"name": "Second Title API Author"}, headers=admin_headers)
    assert first_author_response.status_code == 201
    assert second_author_response.status_code == 201

    first_response = client.post(
        "/books/",
        json={
            "isbn": "1234567890",
            "author_id": first_author_response.json()["id"],
            "title": "Shared Title API Book",
            "published_date": "2023-01-01",
        },
        headers=admin_headers,
    )
    second_response = client.post(
        "/books/",
        json={
            "isbn": "1234567891",
            "author_id": second_author_response.json()["id"],
            "title": "Shared Title API Book",
            "published_date": "2023-01-01",
        },
        headers=admin_headers,
    )

    assert first_response.status_code == 201
    assert second_response.status_code == 201


def test_book_creation_rejects_same_isbn_with_different_author(client, admin_headers):
    first_author_response = client.post("/authors/", json={"name": "First ISBN API Author"}, headers=admin_headers)
    second_author_response = client.post("/authors/", json={"name": "Second ISBN API Author"}, headers=admin_headers)
    assert first_author_response.status_code == 201
    assert second_author_response.status_code == 201

    payload = {
        "isbn": "1234567890",
        "author_id": first_author_response.json()["id"],
        "title": "ISBN Conflict API Book",
        "published_date": "2023-01-01",
    }
    assert client.post("/books/", json=payload, headers=admin_headers).status_code == 201

    conflict_response = client.post(
        "/books/",
        json={**payload, "author_id": second_author_response.json()["id"]},
        headers=admin_headers,
    )

    assert conflict_response.status_code == 409
    assert conflict_response.json()["detail"] == "ISBN already exists for a different book metadata."


def test_author_endpoints_reject_duplicates_and_support_pagination(client, admin_headers):
    response = client.post("/authors/", json={"name": "Duplicate Author"}, headers=admin_headers)
    assert response.status_code == 201

    duplicate_response = client.post("/authors/", json={"name": "Duplicate Author"}, headers=admin_headers)
    assert duplicate_response.status_code == 409

    list_response = client.get("/authors/", params={"skip": 0, "limit": 1})
    assert list_response.status_code == 200
    body = list_response.json()
    assert body["total"] == 1
    assert body["skip"] == 0
    assert body["limit"] == 1
    assert len(body["items"]) == 1


def test_book_availability_by_isbn_distinguishes_missing_and_unavailable(
    client,
    admin_headers,
    user_factory,
    author_factory,
    book_factory,
):
    missing_response = client.get("/books/count/9999999999")
    assert missing_response.status_code == 404

    author = author_factory()
    book = book_factory(author_id=author.id, isbn="1234567890")
    user = user_factory()

    available_response = client.get(f"/books/count/{book.isbn}")
    assert available_response.status_code == 200
    assert available_response.json()["available_exemplars"] == 1

    loan_response = client.post(
        "/loans/",
        params={"user_id": user.id, "book_id": book.id},
        headers=admin_headers,
    )
    assert loan_response.status_code == 201

    unavailable_response = client.get(f"/books/count/{book.isbn}")
    assert unavailable_response.status_code == 200
    assert unavailable_response.json()["available_exemplars"] == 0
    assert unavailable_response.json()["is_available"] is False

    exemplars_response = client.get(f"/books/exemplars/{book.isbn}")
    assert exemplars_response.status_code == 200
    assert exemplars_response.json() == []
