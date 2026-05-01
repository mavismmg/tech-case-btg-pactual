from datetime import date

from app.schemas.author import AuthorCreate
from app.schemas.book import BookCreate
from app.schemas.user import UserCreate
from app.services import author_service, book_service
from app.services.author_service import create_author
from app.services.book_service import create_book
from app.services.book_service import BookHasActiveLoansError, BookNotFoundError
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

    def delete_by_prefix(self, prefix):
        deleted_keys = [key for key in self.values if key.startswith(prefix)]
        self.deleted_keys.extend(deleted_keys)
        for key in deleted_keys:
            self.values.pop(key, None)


def test_count_available_exemplars_uses_cache(db, monkeypatch):
    fake_cache = FakeCache()
    calls = {"count": 0}

    def fake_count(db, isbn):
        calls["count"] += 1
        return 2

    monkeypatch.setattr(book_service, "cache", fake_cache)
    monkeypatch.setattr(book_service.book_repository, "count_active_books_by_isbn", lambda db, isbn: 2)
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


def test_list_books_uses_cache(db, monkeypatch):
    fake_cache = FakeCache()
    monkeypatch.setattr(book_service, "cache", fake_cache)

    author = create_author(db, AuthorCreate(name="Book List Cache Author"))
    create_book(
        db,
        BookCreate(
            isbn="1234567890",
            author_id=author.id,
            title="Book List Cache Book",
            published_date=date(2023, 1, 1),
        ),
    )

    books, total = book_service.list_books(db)
    assert len(books) == 1
    assert total == 1

    def fail_on_cache_hit(db, skip, limit):
        raise AssertionError("repository should not be called on cache hit")

    monkeypatch.setattr(book_service.book_repository, "get_books", fail_on_cache_hit)

    cached_books, cached_total = book_service.list_books(db)
    assert len(cached_books) == 1
    assert cached_total == 1


def test_get_book_uses_cache(db, monkeypatch):
    fake_cache = FakeCache()
    monkeypatch.setattr(book_service, "cache", fake_cache)

    author = create_author(db, AuthorCreate(name="Book Detail Cache Author"))
    book = create_book(
        db,
        BookCreate(
            isbn="1234567890",
            author_id=author.id,
            title="Book Detail Cache Book",
            published_date=date(2023, 1, 1),
        ),
    )

    assert book_service.get_book(db, book.id).id == book.id

    def fail_on_cache_hit(db, book_id):
        raise AssertionError("repository should not be called on cache hit")

    monkeypatch.setattr(book_service.book_repository, "get_book_by_id", fail_on_cache_hit)

    cached_book = book_service.get_book(db, book.id)
    assert cached_book.id == book.id


def test_book_creation_invalidates_book_list_cache(db, monkeypatch):
    fake_cache = FakeCache()
    monkeypatch.setattr(book_service, "cache", fake_cache)

    author = create_author(db, AuthorCreate(name="Book List Invalidation Author"))
    fake_cache.values[book_service._book_list_cache_key(0, 100)] = {"items": [], "total": 0}

    create_book(
        db,
        BookCreate(
            isbn="1234567890",
            author_id=author.id,
            title="Book List Invalidation Book",
            published_date=date(2023, 1, 1),
        ),
    )

    assert book_service._book_list_cache_key(0, 100) not in fake_cache.values
    assert book_service._book_list_cache_key(0, 100) in fake_cache.deleted_keys


def test_delete_book_is_soft_delete_and_blocks_active_loan(db):
    user = create_user(db, UserCreate(name="Book Delete User", email="book-delete@example.com"))
    author = create_author(db, AuthorCreate(name="Book Delete Author"))
    blocked_book = create_book(
        db,
        BookCreate(
            isbn="1234567890",
            author_id=author.id,
            title="Blocked Delete Book",
            published_date=date(2023, 1, 1),
        ),
    )
    deletable_book = create_book(
        db,
        BookCreate(
            isbn="1234567891",
            author_id=author.id,
            title="Deletable Book",
            published_date=date(2023, 1, 1),
        ),
    )
    create_loan(db, user.id, blocked_book.id)

    try:
        book_service.delete_book(db, blocked_book.id)
    except BookHasActiveLoansError:
        pass
    else:
        raise AssertionError("book with active loan should not be deleted")

    deleted_book = book_service.delete_book(db, deletable_book.id)

    assert deleted_book.deleted_at is not None
    assert deleted_book.is_available is False

    try:
        book_service.get_book(db, deletable_book.id)
    except BookNotFoundError:
        pass
    else:
        raise AssertionError("soft deleted book should not be returned by get_book")


def test_list_authors_uses_cache_and_create_author_invalidates_list(db, monkeypatch):
    fake_cache = FakeCache()
    monkeypatch.setattr(author_service, "cache", fake_cache)

    create_author(db, AuthorCreate(name="Author Cache One"))

    authors, total = author_service.list_authors(db)
    assert len(authors) == 1
    assert total == 1

    def fail_on_cache_hit(db, skip, limit):
        raise AssertionError("repository should not be called on cache hit")

    monkeypatch.setattr(author_service.author_repository, "get_authors", fail_on_cache_hit)

    cached_authors, cached_total = author_service.list_authors(db)
    assert len(cached_authors) == 1
    assert cached_total == 1

    create_author(db, AuthorCreate(name="Author Cache Two"))

    assert author_service._author_list_cache_key(0, 100) not in fake_cache.values
    assert author_service._author_list_cache_key(0, 100) in fake_cache.deleted_keys
