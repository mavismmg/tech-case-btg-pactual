from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Sequence
from app.core.database import SessionLocal
from app.schemas.book import BookCreate, BookResponse
from app.services import book_service
from app.services.book_service import BookNotFoundError, BookAuthorNotFoundError, BookCreationError

router = APIRouter(prefix="/books", tags=["Books"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/", response_model=BookResponse, status_code=status.HTTP_201_CREATED)
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

@router.get("/", response_model=list[BookResponse], status_code=status.HTTP_200_OK)
def list_books(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)) -> Sequence[BookResponse]:
    return book_service.list_books(db, skip, limit)

@router.get("/{book_id}", response_model=BookResponse, status_code=status.HTTP_200_OK)
def get_book(book_id: int, db: Session = Depends(get_db)) -> BookResponse:
    try:
        return book_service.get_book(db, book_id)
    except BookNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail=e.message
        )