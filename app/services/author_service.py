import logging

from sqlalchemy.orm import Session
from app.repositories import author_repository
from app.schemas.author import AuthorCreate
from app.models.author import Author

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
    operation = "create_author"
    existing_author = author_repository.get_author_by_name(db, author_data.name)
    if existing_author:
        logger.warning(
            "Author creation blocked because author already exists",
            extra={"operation": operation, "author_id": existing_author.id, "reason": "author_already_exists"},
        )

        raise AuthorAlreadyExistsError(author_data.name)
    
    logger.debug("Starting author creation flow", extra={"operation": operation})

    try:
        new_author = author_repository.create_author(db, author_data)
        logger.info("Author created successfully", extra={"operation": operation, "author_id": new_author.id})

        return new_author

    except AuthorAlreadyExistsError:
        raise
    except Exception as e:
        logger.exception("Unexpected error while creating author", extra={"operation": operation})

        raise AuthorCreationError(author_data.name, e)
    
def list_authors(db: Session, skip: int = 0, limit: int = 100) -> tuple[list[Author], int]:
    logger.debug("Listing authors", extra={"operation": "list_authors", "skip": skip, "limit": limit})
    
    return author_repository.get_authors(db, skip, limit)

def get_author(db: Session, author_id: int) -> Author:
    logger.debug("Fetching author by ID", extra={"operation": "get_author", "author_id": author_id})

    author = author_repository.get_author_by_id(db, author_id)

    if not author:
        logger.warning(
            "Author fetch blocked because author was not found",
            extra={"operation": "get_author", "author_id": author_id, "reason": "author_not_found"},
        )

        raise AuthorNotFoundError(author_id)
    
    return author
