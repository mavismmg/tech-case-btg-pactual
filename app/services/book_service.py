import logging
from datetime import date, datetime

from sqlalchemy.orm import Session
from app.core import cache
from app.models.author import Author
from app.repositories import author_repository, book_repository, loan_repository
from app.schemas.book import BookCreate
from app.models.book import Book

logger = logging.getLogger(__name__)

AVAILABLE_COUNT_CACHE_KEY = "books:available_count:{isbn}"
AVAILABLE_EXEMPLARS_CACHE_KEY = "books:available_exemplars:{isbn}"
BOOK_LIST_CACHE_KEY = "books:list:{skip}:{limit}"
BOOK_DETAIL_CACHE_KEY = "books:detail:{book_id}"
BOOK_LIST_CACHE_PREFIX = "books:list:"
BOOK_CACHE_TTL_SECONDS = 60

class BookNotFoundError(Exception):
    def __init__(self, book_identifier: int | str, identifier_label: str = "ID"):
        self.message = f"Book with {identifier_label} {book_identifier} not found."
        super().__init__(self.message)

class BookAuthorNotFoundError(Exception):
    def __init__(self, author_id: int):
        self.message = f"Author with ID {author_id} not found for the book."
        super().__init__(self.message)

class BookCreationError(Exception):
    def __init__(self, title: str, original_exception: Exception):
        self.message = f"Failed to create book '{title}'. Reason: {str(original_exception)}"
        super().__init__(self.message)


class BookTitleIsbnConflictError(Exception):
    def __init__(self) -> None:
        self.message = "Book title already exists for this author with a different ISBN."
        super().__init__(self.message)


class BookIsbnConflictError(Exception):
    def __init__(self) -> None:
        self.message = "ISBN already exists for a different book metadata."
        super().__init__(self.message)


class BookHasActiveLoansError(Exception):
    def __init__(self, book_id: int):
        self.message = f"Cannot delete book with ID {book_id}. Book has active loans."
        super().__init__(self.message)


def _available_count_cache_key(isbn: str) -> str:
    return AVAILABLE_COUNT_CACHE_KEY.format(isbn=isbn)


def _available_exemplars_cache_key(isbn: str) -> str:
    return AVAILABLE_EXEMPLARS_CACHE_KEY.format(isbn=isbn)


def _book_list_cache_key(skip: int, limit: int) -> str:
    return BOOK_LIST_CACHE_KEY.format(skip=skip, limit=limit)


def _book_detail_cache_key(book_id: int) -> str:
    return BOOK_DETAIL_CACHE_KEY.format(book_id=book_id)


def invalidate_available_exemplars_cache(isbn: str) -> None:
    cache.delete_keys(
        _available_count_cache_key(isbn),
        _available_exemplars_cache_key(isbn),
    )


def invalidate_book_list_cache() -> None:
    cache.delete_by_prefix(BOOK_LIST_CACHE_PREFIX)


def invalidate_book_detail_cache(book_id: int) -> None:
    cache.delete_keys(_book_detail_cache_key(book_id))


def invalidate_book_cache(book_id: int, *isbns: str | None) -> None:
    invalidate_book_detail_cache(book_id)
    invalidate_book_list_cache()
    for isbn in isbns:
        if isbn is not None:
            invalidate_available_exemplars_cache(isbn)


def _serialize_datetime(value: datetime | None) -> str | None:
    if value is None:
        return None

    return value.isoformat()


def _serialize_date(value: date) -> str:
    return value.isoformat()


def _parse_datetime(value: str | None) -> datetime | None:
    if value is None:
        return None

    return datetime.fromisoformat(value)


def _parse_date(value: str) -> date:
    return date.fromisoformat(value)


def _serialize_author(author: Author | None) -> dict | None:
    if author is None:
        return None

    return {
        "id": author.id,
        "name": author.name,
        "created_at": _serialize_datetime(author.created_at),
        "updated_at": _serialize_datetime(author.updated_at),
        "deleted_at": _serialize_datetime(author.deleted_at),
    }


def _serialize_book(book: Book) -> dict:
    return {
        "id": book.id,
        "isbn": book.isbn,
        "author_id": book.author_id,
        "title": book.title,
        "published_date": _serialize_date(book.published_date),
        "is_available": book.is_available,
        "created_at": _serialize_datetime(book.created_at),
        "updated_at": _serialize_datetime(book.updated_at),
        "deleted_at": _serialize_datetime(book.deleted_at),
        "author": _serialize_author(book.author),
    }


def _deserialize_author(data: dict | None) -> Author | None:
    if data is None:
        return None

    return Author(
        id=data["id"],
        name=data["name"],
        created_at=_parse_datetime(data["created_at"]),
        updated_at=_parse_datetime(data["updated_at"]),
        deleted_at=_parse_datetime(data["deleted_at"]),
    )


def _deserialize_book(data: dict) -> Book:
    book = Book(
        id=data["id"],
        isbn=data["isbn"],
        author_id=data["author_id"],
        title=data["title"],
        published_date=_parse_date(data["published_date"]),
        is_available=data["is_available"],
        created_at=_parse_datetime(data["created_at"]),
        updated_at=_parse_datetime(data["updated_at"]),
        deleted_at=_parse_datetime(data["deleted_at"]),
    )
    book.author = _deserialize_author(data.get("author"))
    return book


def create_book(db: Session, book_data: BookCreate) -> Book:
    operation = "create_book"
    existing_author = author_repository.get_author_by_id(db, book_data.author_id)
    if not existing_author:
        logger.warning(
            "Book creation blocked because author was not found",
            extra={"operation": operation, "author_id": book_data.author_id, "reason": "author_not_found"},
        )

        raise BookAuthorNotFoundError(book_data.author_id)

    existing_book_with_title = book_repository.get_active_book_by_author_and_title(
        db,
        book_data.author_id,
        book_data.title,
    )
    if existing_book_with_title is not None and existing_book_with_title.isbn != book_data.isbn:
        logger.warning(
            "Book creation blocked because title already exists for author with another ISBN",
            extra={
                "operation": operation,
                "author_id": book_data.author_id,
                "title": book_data.title,
                "existing_isbn": existing_book_with_title.isbn,
                "requested_isbn": book_data.isbn,
                "reason": "title_isbn_conflict",
            },
        )
        raise BookTitleIsbnConflictError()

    existing_book_with_isbn = book_repository.get_active_book_by_isbn(db, book_data.isbn)
    if (
        existing_book_with_isbn is not None
        and (
            existing_book_with_isbn.author_id != book_data.author_id
            or existing_book_with_isbn.title != book_data.title
            or existing_book_with_isbn.published_date != book_data.published_date
        )
    ):
        logger.warning(
            "Book creation blocked because ISBN already exists with different metadata",
            extra={
                "operation": operation,
                "isbn": book_data.isbn,
                "existing_book_id": existing_book_with_isbn.id,
                "existing_author_id": existing_book_with_isbn.author_id,
                "requested_author_id": book_data.author_id,
                "existing_title": existing_book_with_isbn.title,
                "requested_title": book_data.title,
                "existing_published_date": existing_book_with_isbn.published_date.isoformat(),
                "requested_published_date": book_data.published_date.isoformat(),
                "reason": "isbn_metadata_conflict",
            },
        )
        raise BookIsbnConflictError()

    try:
        new_book = book_repository.create_book(db, book_data)
        invalidate_available_exemplars_cache(new_book.isbn)
        invalidate_book_list_cache()
        logger.info(
            "Book created successfully",
            extra={
                "operation": operation,
                "book_id": new_book.id,
                "author_id": new_book.author_id,
                "isbn": new_book.isbn,
            },
        )

        return new_book

    except (BookAuthorNotFoundError, BookTitleIsbnConflictError, BookIsbnConflictError):
        raise
    except Exception as e:
        logger.exception(
            "Unexpected error while creating book",
            extra={"operation": operation, "author_id": book_data.author_id, "isbn": book_data.isbn},
        )

        raise BookCreationError(book_data.title, e)

def list_books(db: Session, skip: int = 0, limit: int = 100) -> tuple[list[Book], int]:
    logger.debug("Listing books", extra={"operation": "list_books", "skip": skip, "limit": limit})

    cache_key = _book_list_cache_key(skip, limit)
    cached_books = cache.get_json(cache_key)
    if cached_books is not None:
        return [_deserialize_book(book) for book in cached_books["items"]], int(cached_books["total"])

    books, total = book_repository.get_books(db, skip, limit)
    cache.set_json(
        cache_key,
        {"items": [_serialize_book(book) for book in books], "total": total},
        BOOK_CACHE_TTL_SECONDS,
    )
    return books, total

def get_book(db: Session, book_id: int) -> Book:
    logger.debug("Fetching book by ID", extra={"operation": "get_book", "book_id": book_id})

    cache_key = _book_detail_cache_key(book_id)
    cached_book = cache.get_json(cache_key)
    if cached_book is not None:
        return _deserialize_book(cached_book)

    book = book_repository.get_book_by_id(db, book_id)

    if not book:
        logger.warning(
            "Book fetch blocked because book was not found",
            extra={"operation": "get_book", "book_id": book_id, "reason": "book_not_found"},
        )

        raise BookNotFoundError(book_id)

    cache.set_json(cache_key, _serialize_book(book), BOOK_CACHE_TTL_SECONDS)
    return book


def _get_book_for_write(db: Session, book_id: int, operation: str) -> Book:
    book = book_repository.get_book_by_id(db, book_id)

    if not book:
        logger.warning(
            "Book write operation blocked because book was not found",
            extra={"operation": operation, "book_id": book_id, "reason": "book_not_found"},
        )
        raise BookNotFoundError(book_id)

    return book


def delete_book(db: Session, book_id: int) -> Book:
    operation = "delete_book"
    book = _get_book_for_write(db, book_id, operation)

    active_loans = loan_repository.get_active_loans_count_by_book_id(db, book_id)
    if active_loans > 0:
        logger.warning(
            "Book deletion blocked because book has active loans",
            extra={
                "operation": operation,
                "book_id": book_id,
                "active_loans": active_loans,
                "reason": "active_loans_exist",
            },
        )
        raise BookHasActiveLoansError(book_id)

    try:
        deleted_book = book_repository.soft_delete_book(db, book)
        invalidate_book_cache(deleted_book.id, deleted_book.isbn)
        logger.info("Book soft deleted successfully", extra={"operation": operation, "book_id": book_id})

        return deleted_book
    except (BookNotFoundError, BookHasActiveLoansError):
        raise
    except Exception:
        logger.exception("Unexpected error while deleting book", extra={"operation": operation, "book_id": book_id})
        raise

def count_available_exemplars(db: Session, isbn: str) -> int:
    logger.debug("Counting available exemplars", extra={"operation": "count_available_exemplars", "isbn": isbn})

    if book_repository.count_active_books_by_isbn(db, isbn) == 0:
        logger.warning(
            "Available exemplars count blocked because ISBN was not found",
            extra={"operation": "count_available_exemplars", "isbn": isbn, "reason": "isbn_not_found"},
        )
        raise BookNotFoundError(isbn, "ISBN")

    cache_key = _available_count_cache_key(isbn)
    cached_count = cache.get_json(cache_key)
    if cached_count is not None:
        return int(cached_count)

    available_count = book_repository.count_exemplars_by_isbn(db, isbn)
    cache.set_json(cache_key, available_count, BOOK_CACHE_TTL_SECONDS)
    return available_count

def get_exemplars_by_isbn(db: Session, isbn: str) -> list[Book]:
    logger.debug("Fetching exemplars by ISBN", extra={"operation": "get_exemplars_by_isbn", "isbn": isbn})

    if book_repository.count_active_books_by_isbn(db, isbn) == 0:
        logger.warning(
            "Available exemplars fetch blocked because ISBN was not found",
            extra={"operation": "get_exemplars_by_isbn", "isbn": isbn, "reason": "isbn_not_found"},
        )
        raise BookNotFoundError(isbn, "ISBN")

    cache_key = _available_exemplars_cache_key(isbn)
    cached_exemplars = cache.get_json(cache_key)
    if cached_exemplars is not None:
        return [_deserialize_book(book) for book in cached_exemplars]

    exemplars = book_repository.get_exemplars_by_isbn(db, isbn)
    cache.set_json(
        cache_key,
        [_serialize_book(book) for book in exemplars],
        BOOK_CACHE_TTL_SECONDS,
    )
    return exemplars
