from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.schemas.user import UserCreate, UserResponse
from app.services import user_service
from app.services.user_service import UserNotFoundError

router = APIRouter(prefix="/users", tags=["Users"])

def get_db():
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()

@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(user: UserCreate, db: Session = Depends(get_db)):
    return user_service.create_user(db, user)

@router.get("/", response_model=list[UserResponse], status_code=status.HTTP_200_OK)
def list_users(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return user_service.list_users(db, skip, limit)

@router.get("/{user_id}", response_model=UserResponse, status_code=status.HTTP_200_OK)
def get_user(user_id: int, db: Session = Depends(get_db)):
    try:
        return user_service.get_user_by_id(db, user_id)
    except UserNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail=e.message
        )