import logging

from sqlalchemy.orm import Session
from app.repositories import book_repository
from app.schemas.book import BookCreate
from app.models.book import Book

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class BookNotFoundError(Exception):
    def __init__(self, book_id: int):
        self.message = f"Book with ID {book_id} not found."
        super().__init__(self.message)

def create_book(db: Session, book_data: BookCreate) -> Book:
    logger.info(f"Creating book: {book_data.title} by {book_data.author}, published in {book_data.published_date}")

    try:
        new_book = book_repository.create_book(db, book_data)
        logger.info(f"Successfully created book. ID: {new_book.id}")

        return new_book

    except Exception as e:
        logger.error(f"Error while creating book '{book_data.title}': {str(e)}", exc_info=True)

        raise e

def list_books(db: Session, skip: int = 0, limit: int = 100) -> list[Book]:
    logger.info(f"Listing books with skip={skip} and limit={limit}")
    
    return book_repository.get_books(db, skip, limit)

def get_book(db: Session, book_id: int) -> Book:
    logger.info(f"Fetching book with ID: {book_id}")

    book = book_repository.get_book_by_id(db, book_id)

    if not book:
        logger.warning(f"Book with ID {book_id} not found")

        raise BookNotFoundError(book_id)
    
    return book