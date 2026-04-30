from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from app.models.author import Author
from app.schemas.author import AuthorCreate

import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_author(db: Session, author_data: AuthorCreate) -> Author:
    db_author = Author(**author_data.model_dump())

    try:
        db.add(db_author)
        db.commit()
        db.refresh(db_author)

        logger.info(f"Created author with success: {db_author.id} - Name: {db_author.name}")

        return db_author
    except SQLAlchemyError as e:
        db.rollback()

        logger.error(f"Error while creating author: {str(e)}", exc_info=True)

        raise e
    
def get_authors(db: Session, skip: int = 0, limit: int = 100) -> tuple[list[Author], int]:
    logger.info("Fetching authors from database")
    
    query = db.query(Author)
    total = query.count()
    authors = query.order_by(Author.created_at).offset(skip).limit(limit).all()
    return authors, total

def get_author_by_id(db: Session, author_id: int) -> Author | None:
    logger.info(f"Fetching author with ID: {author_id}")

    return db.get(Author, author_id)

def get_author_by_name(db: Session, name: str) -> Author | None:
    logger.info(f"Fetching author with name: {name}")

    return db.query(Author).filter(Author.name == name).first()