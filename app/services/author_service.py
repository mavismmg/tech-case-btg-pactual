import logging
from datetime import datetime

from sqlalchemy.orm import Session
from app.core import cache
from app.repositories import author_repository
from app.schemas.author import AuthorCreate
from app.models.author import Author

logger = logging.getLogger(__name__)
AUTHOR_LIST_CACHE_KEY = "authors:list:{skip}:{limit}"
AUTHOR_DETAIL_CACHE_KEY = "authors:detail:{author_id}"
AUTHOR_LIST_CACHE_PREFIX = "authors:list:"
AUTHOR_CACHE_TTL_SECONDS = 300

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


def _author_list_cache_key(skip: int, limit: int) -> str:
    return AUTHOR_LIST_CACHE_KEY.format(skip=skip, limit=limit)


def _author_detail_cache_key(author_id: int) -> str:
    return AUTHOR_DETAIL_CACHE_KEY.format(author_id=author_id)


def _serialize_datetime(value: datetime | None) -> str | None:
    if value is None:
        return None

    return value.isoformat()


def _parse_datetime(value: str | None) -> datetime | None:
    if value is None:
        return None

    return datetime.fromisoformat(value)


def _serialize_author(author: Author) -> dict:
    return {
        "id": author.id,
        "name": author.name,
        "created_at": _serialize_datetime(author.created_at),
        "updated_at": _serialize_datetime(author.updated_at),
        "deleted_at": _serialize_datetime(author.deleted_at),
    }


def _deserialize_author(data: dict) -> Author:
    return Author(
        id=data["id"],
        name=data["name"],
        created_at=_parse_datetime(data["created_at"]),
        updated_at=_parse_datetime(data["updated_at"]),
        deleted_at=_parse_datetime(data["deleted_at"]),
    )


def invalidate_author_list_cache() -> None:
    cache.delete_by_prefix(AUTHOR_LIST_CACHE_PREFIX)

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
        invalidate_author_list_cache()
        logger.info("Author created successfully", extra={"operation": operation, "author_id": new_author.id})

        return new_author

    except AuthorAlreadyExistsError:
        raise
    except Exception as e:
        logger.exception("Unexpected error while creating author", extra={"operation": operation})

        raise AuthorCreationError(author_data.name, e)
    
def list_authors(db: Session, skip: int = 0, limit: int = 100) -> tuple[list[Author], int]:
    logger.debug("Listing authors", extra={"operation": "list_authors", "skip": skip, "limit": limit})

    cache_key = _author_list_cache_key(skip, limit)
    cached_authors = cache.get_json(cache_key)
    if cached_authors is not None:
        return [_deserialize_author(author) for author in cached_authors["items"]], int(cached_authors["total"])

    authors, total = author_repository.get_authors(db, skip, limit)
    cache.set_json(
        cache_key,
        {"items": [_serialize_author(author) for author in authors], "total": total},
        AUTHOR_CACHE_TTL_SECONDS,
    )
    return authors, total

def get_author(db: Session, author_id: int) -> Author:
    logger.debug("Fetching author by ID", extra={"operation": "get_author", "author_id": author_id})

    cache_key = _author_detail_cache_key(author_id)
    cached_author = cache.get_json(cache_key)
    if cached_author is not None:
        return _deserialize_author(cached_author)

    author = author_repository.get_author_by_id(db, author_id)

    if not author:
        logger.warning(
            "Author fetch blocked because author was not found",
            extra={"operation": "get_author", "author_id": author_id, "reason": "author_not_found"},
        )

        raise AuthorNotFoundError(author_id)

    cache.set_json(cache_key, _serialize_author(author), AUTHOR_CACHE_TTL_SECONDS)
    return author
