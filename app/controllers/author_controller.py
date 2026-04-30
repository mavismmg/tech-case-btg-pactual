from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Sequence
from app.core.database import SessionLocal
from app.schemas.author import AuthorCreate, AuthorResponse
from app.services import author_service
from app.services.author_service import AuthorNotFoundError, AuthorCreationError, AuthorAlreadyExistsError

router = APIRouter(prefix="/authors", tags=["Authors"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/", response_model=AuthorResponse, status_code=status.HTTP_201_CREATED)
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

@router.get("/", response_model=list[AuthorResponse], status_code=status.HTTP_200_OK)
def get_authors(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)) -> Sequence[AuthorResponse]:
    return author_service.list_authors(db, skip, limit)

@router.get("/{author_id}", response_model=AuthorResponse, status_code=status.HTTP_200_OK)
def get_author(author_id: int, db: Session = Depends(get_db)) -> AuthorResponse:
    try:
        return author_service.get_author(db, author_id)
    except AuthorNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail=e.message
        )