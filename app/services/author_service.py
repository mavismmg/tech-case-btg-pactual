import logging

from sqlalchemy.orm import Session
from app.repositories import author_repository
from app.schemas.author import AuthorCreate
from app.models.author import Author

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AuthorCreationError(Exception):
    def __init__(self, name: str, original_exception: Exception):
        self.message = f"Failed to create author '{name}'. Reason: {str(original_exception)}"
        super().__init__(self.message)

class AuthorNotFoundError(Exception):
    def __init__(self, author_id: int):
        self.message = f"Author with ID {author_id} not found."
        super().__init__(self.message)

class AuthorAlreadyExistsError(Exception):
    def __init__(self, name: str):
        self.message = f"Author with name '{name}' already exists."
        super().__init__(self.message)

def create_author(db: Session, author_data: AuthorCreate) -> Author:
    existing_author = author_repository.get_author_by_name(db, author_data.name)
    if existing_author:
        logger.warning(f"Attempt to create duplicate author with name: {author_data.name}")

        raise AuthorAlreadyExistsError(author_data.name)
    
    logger.info(f"Creating author: {author_data.name}")

    try:
        new_author = author_repository.create_author(db, author_data)
        logger.info(f"Successfully created author. ID: {new_author.id}")

        return new_author

    except AuthorCreationError as e:
        logger.error(f"Error while creating author '{author_data.name}': {str(e)}", exc_info=True)

        raise AuthorCreationError(author_data.name, e)
    
def list_authors(db: Session, skip: int = 0, limit: int = 100) -> list[Author]:
    logger.info(f"Listing authors with skip={skip} and limit={limit}")
    
    return author_repository.get_authors(db, skip, limit)

def get_author(db: Session, author_id: int) -> Author:
    logger.info(f"Fetching author with ID: {author_id}")

    author = author_repository.get_author_by_id(db, author_id)

    if not author:
        logger.warning(f"Author with ID {author_id} not found")

        raise AuthorNotFoundError(author_id)
    
    return author