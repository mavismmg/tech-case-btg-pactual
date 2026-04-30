from sqlalchemy.orm import Session, joinedload
from sqlalchemy.exc import SQLAlchemyError
from app.models.book import Book
from app.schemas.book import BookCreate

import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_book(db: Session, book_data: BookCreate) -> Book:
    db_book = Book(
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

def get_books(db: Session, skip: int = 0, limit: int = 100) -> list[Book]:
    logger.info("Fetching books from database")
    
    return (
        db.query(Book)
        .options(joinedload(Book.author))
        .order_by(Book.published_date)
        .offset(skip)
        .limit(limit)
        .all()
    )

def get_book_by_id(db: Session, book_id: int) -> Book | None:
    logger.info(f"Fetching book with ID: {book_id}")

    return (
        db.query(Book)
        .options(joinedload(Book.author))
        .filter(Book.id == book_id)
        .one_or_none()
    )