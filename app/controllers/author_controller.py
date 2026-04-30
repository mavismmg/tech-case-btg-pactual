from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.dependencies import get_db
from app.dependencies import require_roles
from app.core.rate_limit import rate_limit
from app.models.account import AccountRole
from app.schemas.author import AuthorCreate, AuthorResponse
from app.schemas.common import PaginatedResponse
from app.services import author_service
from app.services.author_service import AuthorNotFoundError, AuthorCreationError, AuthorAlreadyExistsError

router = APIRouter(prefix="/authors", tags=["Authors"])
librarian_or_admin = Depends(require_roles(AccountRole.ADMIN, AccountRole.LIBRARIAN))

@router.post(
    "/",
    response_model=AuthorResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[librarian_or_admin, Depends(rate_limit(limit=10))],
)
def create_author(author: AuthorCreate, db: Session = Depends(get_db)) -> AuthorResponse:
    try:
        return author_service.create_author(db, author)
    except AuthorCreationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail=e.message
        )
    except AuthorAlreadyExistsError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=e.message
        )

@router.get("/", response_model=PaginatedResponse[AuthorResponse], status_code=status.HTTP_200_OK)
def get_authors(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)) -> PaginatedResponse[AuthorResponse]:
    authors, total = author_service.list_authors(db, skip, limit)
    author_responses = [AuthorResponse.model_validate(author) for author in authors]
    return PaginatedResponse(items=author_responses, total=total, skip=skip, limit=limit)

@router.get("/{author_id}", response_model=AuthorResponse, status_code=status.HTTP_200_OK)
def get_author(author_id: int, db: Session = Depends(get_db)) -> AuthorResponse:
    try:
        return author_service.get_author(db, author_id)
    except AuthorNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail=e.message
        )
