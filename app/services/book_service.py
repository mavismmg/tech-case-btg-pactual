import logging
from datetime import date, datetime

from sqlalchemy.orm import Session
from app.core import cache
from app.models.author import Author
from app.repositories import author_repository, book_repository
from app.schemas.book import BookCreate
from app.models.book import Book

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

AVAILABLE_COUNT_CACHE_KEY = "books:available_count:{isbn}"
AVAILABLE_EXEMPLARS_CACHE_KEY = "books:available_exemplars:{isbn}"
BOOK_CACHE_TTL_SECONDS = 60

class BookNotFoundError(Exception):
    def __init__(self, book_id: int):
        self.message = f"Book with ID {book_id} not found."
        super().__init__(self.message)

class BookAuthorNotFoundError(Exception):
    def __init__(self, author_id: int):
        self.message = f"Author with ID {author_id} not found for the book."
        super().__init__(self.message)

class BookCreationError(Exception):
    def __init__(self, title: str, original_exception: Exception):
        self.message = f"Failed to create book '{title}'. Reason: {str(original_exception)}"
        super().__init__(self.message)


def _available_count_cache_key(isbn: str) -> str:
    return AVAILABLE_COUNT_CACHE_KEY.format(isbn=isbn)


def _available_exemplars_cache_key(isbn: str) -> str:
    return AVAILABLE_EXEMPLARS_CACHE_KEY.format(isbn=isbn)


def invalidate_available_exemplars_cache(isbn: str) -> None:
    cache.delete_keys(
        _available_count_cache_key(isbn),
        _available_exemplars_cache_key(isbn),
    )


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
    existing_author = author_repository.get_author_by_id(db, book_data.author_id)
    if not existing_author:
        logger.warning(f"Attempt to create book with non-existent author ID: {book_data.author_id}")

        raise BookAuthorNotFoundError(book_data.author_id)

    try:
        new_book = book_repository.create_book(db, book_data)
        invalidate_available_exemplars_cache(new_book.isbn)
        logger.info(f"Successfully created book. ID: {new_book.id}")

        return new_book

    except BookCreationError as e:
        logger.error(f"Error while creating book '{book_data.title}': {str(e)}", exc_info=True)

        raise BookCreationError(book_data.title, e)

def list_books(db: Session, skip: int = 0, limit: int = 100) -> tuple[list[Book], int]:
    logger.info(f"Listing books with skip={skip} and limit={limit}")
    
    return book_repository.get_books(db, skip, limit)

def get_book(db: Session, book_id: int) -> Book:
    logger.info(f"Fetching book with ID: {book_id}")

    book = book_repository.get_book_by_id(db, book_id)

    if not book:
        logger.warning(f"Book with ID {book_id} not found")

        raise BookNotFoundError(book_id)
    
    return book

def count_available_exemplars(db: Session, isbn: str) -> int:
    logger.info(f"Counting available exemplars for ISBN: {isbn}")

    cache_key = _available_count_cache_key(isbn)
    cached_count = cache.get_json(cache_key)
    if cached_count is not None:
        return int(cached_count)

    available_count = book_repository.count_exemplars_by_isbn(db, isbn)
    cache.set_json(cache_key, available_count, BOOK_CACHE_TTL_SECONDS)
    return available_count

def get_exemplars_by_isbn(db: Session, isbn: str) -> list[Book]:
    logger.info(f"Fetching exemplars for ISBN: {isbn}")

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
