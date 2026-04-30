from datetime import date

from app.schemas.author import AuthorCreate
from app.schemas.book import BookCreate
from app.schemas.user import UserCreate
from app.services import book_service
from app.services.author_service import create_author
from app.services.book_service import create_book
from app.services.loan_service import create_loan, return_loan
from app.services.user_service import create_user


class FakeCache:
    def __init__(self):
        self.values = {}
        self.deleted_keys = []

    def get_json(self, key):
        return self.values.get(key)

    def set_json(self, key, value, ttl_seconds=60):
        self.values[key] = value

    def delete_keys(self, *keys):
        self.deleted_keys.extend(keys)
        for key in keys:
            self.values.pop(key, None)


def test_count_available_exemplars_uses_cache(db, monkeypatch):
    fake_cache = FakeCache()
    calls = {"count": 0}

    def fake_count(db, isbn):
        calls["count"] += 1
        return 2

    monkeypatch.setattr(book_service, "cache", fake_cache)
    monkeypatch.setattr(book_service.book_repository, "count_exemplars_by_isbn", fake_count)

    assert book_service.count_available_exemplars(db, "1234567890") == 2
    assert book_service.count_available_exemplars(db, "1234567890") == 2
    assert calls["count"] == 1


def test_get_exemplars_by_isbn_uses_cache(db, monkeypatch):
    fake_cache = FakeCache()
    monkeypatch.setattr(book_service, "cache", fake_cache)

    author = create_author(db, AuthorCreate(name="Cache Author"))
    book = create_book(
        db,
        BookCreate(
            isbn="1234567890",
            author_id=author.id,
            title="Cache Book",
            published_date=date(2023, 1, 1),
        ),
    )

    first_result = book_service.get_exemplars_by_isbn(db, book.isbn)
    assert len(first_result) == 1

    def fail_on_cache_hit(db, isbn):
        raise AssertionError("repository should not be called on cache hit")

    monkeypatch.setattr(book_service.book_repository, "get_exemplars_by_isbn", fail_on_cache_hit)

    cached_result = book_service.get_exemplars_by_isbn(db, book.isbn)
    assert len(cached_result) == 1
    assert cached_result[0].id == book.id
    assert cached_result[0].author.name == author.name


def test_available_exemplars_cache_is_invalidated_on_loan_lifecycle(db, monkeypatch):
    fake_cache = FakeCache()
    monkeypatch.setattr(book_service, "cache", fake_cache)

    user = create_user(db, UserCreate(name="Loan Cache User", email="loan-cache@example.com"))
    author = create_author(db, AuthorCreate(name="Loan Cache Author"))
    book = create_book(
        db,
        BookCreate(
            isbn="1234567890",
            author_id=author.id,
            title="Loan Cache Book",
            published_date=date(2023, 1, 1),
        ),
    )

    assert book_service.count_available_exemplars(db, book.isbn) == 1
    assert book_service.get_exemplars_by_isbn(db, book.isbn)[0].id == book.id
    assert fake_cache.values

    loan = create_loan(db, user.id, book.id)

    count_key = book_service._available_count_cache_key(book.isbn)
    exemplars_key = book_service._available_exemplars_cache_key(book.isbn)
    assert count_key not in fake_cache.values
    assert exemplars_key not in fake_cache.values
    assert count_key in fake_cache.deleted_keys
    assert exemplars_key in fake_cache.deleted_keys
    assert book_service.count_available_exemplars(db, book.isbn) == 0

    return_loan(db, loan.id)

    assert count_key not in fake_cache.values
    assert exemplars_key not in fake_cache.values
    assert book_service.count_available_exemplars(db, book.isbn) == 1
