from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Sequence
from app.dependencies import get_db
from app.dependencies import require_roles
from app.core.rate_limit import rate_limit
from app.models.account import AccountRole
from app.schemas.book import AvailableExemplarsCountResponse, BookCreate, BookResponse
from app.schemas.common import PaginatedResponse
from app.services import book_service
from app.services.book_service import BookNotFoundError, BookAuthorNotFoundError, BookCreationError

router = APIRouter(prefix="/books", tags=["Books"])
librarian_or_admin = Depends(require_roles(AccountRole.ADMIN, AccountRole.LIBRARIAN))

@router.post(
    "/",
    response_model=BookResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[librarian_or_admin, Depends(rate_limit(limit=10))],
)
def create_book(book: BookCreate, db: Session = Depends(get_db)) -> BookResponse:
    try:
        return book_service.create_book(db, book)
    except BookCreationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail=str(e)
        )
    except BookAuthorNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )

@router.get(
    "/",
    response_model=PaginatedResponse[BookResponse],
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(rate_limit(limit=60))],
)
def list_books(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)) -> PaginatedResponse[BookResponse]:
    books, total = book_service.list_books(db, skip, limit)
    book_responses = [BookResponse.model_validate(book) for book in books]
    return PaginatedResponse(items=book_responses, total=total, skip=skip, limit=limit)

@router.get("/count/{isbn}", response_model=AvailableExemplarsCountResponse, status_code=status.HTTP_200_OK)
def count_available_exemplars(isbn: str, db: Session = Depends(get_db)) -> AvailableExemplarsCountResponse:
    try:
        available_exemplars = book_service.count_available_exemplars(db, isbn)
        return AvailableExemplarsCountResponse(
            isbn=isbn,
            available_exemplars=available_exemplars,
            is_available=available_exemplars > 0,
            message=(
                f"There are {available_exemplars} available exemplars for ISBN {isbn}."
                if available_exemplars > 0
                else f"There are no available exemplars for ISBN {isbn}."
            ),
        )
    except BookNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    
@router.get("/exemplars/{isbn}", response_model=list[BookResponse], status_code=status.HTTP_200_OK)
def get_exemplars_by_isbn(isbn: str, db: Session = Depends(get_db)) -> Sequence[BookResponse]:
    try:
        return book_service.get_exemplars_by_isbn(db, isbn)
    except BookNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )

@router.get(
    "/{book_id}",
    response_model=BookResponse,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(rate_limit(limit=120))],
)
def get_book(book_id: int, db: Session = Depends(get_db)) -> BookResponse:
    try:
        return book_service.get_book(db, book_id)
    except BookNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail=e.message
        )
