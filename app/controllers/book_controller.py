from collections.abc import Sequence

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.dependencies import get_db
from app.dependencies import require_roles
from app.core.rate_limit import rate_limit
from app.models.account import AccountRole
from app.schemas.book import AvailableExemplarsCountResponse, BookCreate, BookResponse
from app.schemas.common import PaginatedResponse
from app.schemas.params import IsbnPath, PaginationLimit, PaginationSkip, PositivePathId
from app.services import book_service
from app.services.book_service import (
    BookAuthorNotFoundError,
    BookCreationError,
    BookHasActiveLoansError,
    BookIsbnConflictError,
    BookNotFoundError,
    BookTitleIsbnConflictError,
)

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
    except (BookTitleIsbnConflictError, BookIsbnConflictError) as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=e.message,
        )

@router.get(
    "/",
    response_model=PaginatedResponse[BookResponse],
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(rate_limit(limit=60))],
)
def list_books(
    skip: PaginationSkip = 0,
    limit: PaginationLimit = 100,
    db: Session = Depends(get_db),
) -> PaginatedResponse[BookResponse]:
    books, total = book_service.list_books(db, skip, limit)
    book_responses = [BookResponse.model_validate(book) for book in books]
    return PaginatedResponse(items=book_responses, total=total, skip=skip, limit=limit)

@router.get("/count/{isbn}", response_model=AvailableExemplarsCountResponse, status_code=status.HTTP_200_OK)
def count_available_exemplars(isbn: IsbnPath, db: Session = Depends(get_db)) -> AvailableExemplarsCountResponse:
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
def get_exemplars_by_isbn(isbn: IsbnPath, db: Session = Depends(get_db)) -> Sequence[BookResponse]:
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
def get_book(book_id: PositivePathId, db: Session = Depends(get_db)) -> BookResponse:
    try:
        return book_service.get_book(db, book_id)
    except BookNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail=e.message
        )


@router.delete(
    "/{book_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[librarian_or_admin, Depends(rate_limit(limit=10))],
)
def delete_book(book_id: PositivePathId, db: Session = Depends(get_db)) -> None:
    try:
        book_service.delete_book(db, book_id)
    except BookNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message
        )
    except BookHasActiveLoansError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=e.message
        )
