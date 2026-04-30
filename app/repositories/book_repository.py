from sqlalchemy.orm import Session, joinedload
from sqlalchemy.exc import SQLAlchemyError
from app.models.book import Book
from app.schemas.book import BookCreate

import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_book(db: Session, book_data: BookCreate) -> Book:
    db_book = Book(
        isbn=book_data.isbn,
        author_id=book_data.author_id,
        title=book_data.title,
        published_date=book_data.published_date
    )

    try:
        db.add(db_book)
        db.commit()
        db.refresh(db_book)

        logger.info(f"Created book with success: {db_book.id} - {db_book.title}")

        return db_book
    except SQLAlchemyError as e:
        db.rollback()

        logger.error(f"Error while creating book: {str(e)}", exc_info=True)

        raise e

def get_books(db: Session, skip: int = 0, limit: int = 100) -> tuple[list[Book], int]:
    logger.info("Fetching books from database")
    
    query = db.query(Book).options(joinedload(Book.author))
    total = query.count()
    books = query.order_by(Book.published_date).offset(skip).limit(limit).all()
    return books, total

def get_book_by_id(db: Session, book_id: int) -> Book | None:
    logger.info(f"Fetching book with ID: {book_id}")

    return (
        db.query(Book)
        .options(joinedload(Book.author))
        .filter(Book.id == book_id)
        .with_for_update()
        .first()
    )

def count_exemplars_by_isbn(db: Session, isbn: str) -> int:
    logger.info(f"Counting exemplars for ISBN: {isbn}")

    return db.query(Book).filter(Book.isbn == isbn, Book.is_available == True).count()

def get_exemplars_by_isbn(db: Session, isbn: str) -> list[Book]:
    logger.info(f"Fetching exemplars for ISBN: {isbn}")

    return db.query(Book).options(joinedload(Book.author)).filter(Book.isbn == isbn, Book.is_available == True).all()
