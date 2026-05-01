from datetime import date

import pytest

from app.schemas.author import AuthorCreate
from app.schemas.book import BookCreate
from app.services.author_service import create_author
from app.services.book_service import BookIsbnConflictError, BookTitleIsbnConflictError, create_book, delete_book


def _book_data(
    author_id: int,
    isbn: str,
    title: str = "Consistent Title",
    published_date: date = date(2023, 1, 1),
) -> BookCreate:
    return BookCreate(
        isbn=isbn,
        author_id=author_id,
        title=title,
        published_date=published_date,
    )


def test_create_book_allows_first_book(db):
    author = create_author(db, AuthorCreate(name="First Book Author"))

    book = create_book(db, _book_data(author.id, "1234567890"))

    assert book.id is not None
    assert book.title == "Consistent Title"
    assert book.isbn == "1234567890"


def test_create_book_allows_additional_exemplar_with_same_title_author_and_isbn(db):
    author = create_author(db, AuthorCreate(name="Same ISBN Author"))
    create_book(db, _book_data(author.id, "1234567890"))

    second_exemplar = create_book(db, _book_data(author.id, "1234567890"))

    assert second_exemplar.id is not None
    assert second_exemplar.isbn == "1234567890"


def test_create_book_blocks_same_title_and_author_with_different_isbn(db):
    author = create_author(db, AuthorCreate(name="Conflict Author"))
    create_book(db, _book_data(author.id, "1234567890"))

    with pytest.raises(BookTitleIsbnConflictError):
        create_book(db, _book_data(author.id, "1234567891"))


def test_create_book_allows_same_title_for_different_authors(db):
    first_author = create_author(db, AuthorCreate(name="First Same Title Author"))
    second_author = create_author(db, AuthorCreate(name="Second Same Title Author"))
    create_book(db, _book_data(first_author.id, "1234567890"))

    book = create_book(db, _book_data(second_author.id, "1234567891"))

    assert book.author_id == second_author.id
    assert book.title == "Consistent Title"


def test_create_book_blocks_same_isbn_with_different_author(db):
    first_author = create_author(db, AuthorCreate(name="First ISBN Author"))
    second_author = create_author(db, AuthorCreate(name="Second ISBN Author"))
    create_book(db, _book_data(first_author.id, "1234567890"))

    with pytest.raises(BookIsbnConflictError):
        create_book(db, _book_data(second_author.id, "1234567890"))


def test_create_book_blocks_same_isbn_with_different_title(db):
    author = create_author(db, AuthorCreate(name="ISBN Title Conflict Author"))
    create_book(db, _book_data(author.id, "1234567890", title="Original Title"))

    with pytest.raises(BookIsbnConflictError):
        create_book(db, _book_data(author.id, "1234567890", title="Other Title"))


def test_create_book_blocks_same_isbn_with_different_published_date(db):
    author = create_author(db, AuthorCreate(name="ISBN Date Conflict Author"))
    create_book(db, _book_data(author.id, "1234567890"))

    with pytest.raises(BookIsbnConflictError):
        create_book(db, _book_data(author.id, "1234567890", published_date=date(2024, 1, 1)))


def test_create_book_ignores_soft_deleted_title_isbn_conflict(db):
    author = create_author(db, AuthorCreate(name="Soft Delete Conflict Author"))
    deleted_book = create_book(db, _book_data(author.id, "1234567890"))
    delete_book(db, deleted_book.id)

    new_book = create_book(db, _book_data(author.id, "1234567891"))

    assert new_book.id != deleted_book.id
    assert new_book.isbn == "1234567891"


def test_create_book_ignores_soft_deleted_isbn_metadata_conflict(db):
    first_author = create_author(db, AuthorCreate(name="Soft Deleted ISBN First Author"))
    second_author = create_author(db, AuthorCreate(name="Soft Deleted ISBN Second Author"))
    deleted_book = create_book(db, _book_data(first_author.id, "1234567890"))
    delete_book(db, deleted_book.id)

    new_book = create_book(db, _book_data(second_author.id, "1234567890"))

    assert new_book.id != deleted_book.id
    assert new_book.author_id == second_author.id
