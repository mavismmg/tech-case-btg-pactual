from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.schemas.user import UserCreate, UserResponse
from app.services import user_service


router = APIRouter(prefix="/users", tags=["Users"])

def get_db():
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()

@router.post("/", response_model=UserResponse)
def create_user(user: UserCreate, db: Session = Depends(get_db)):
    existing_user = user_service.list_users(db)

    if any(u.email == user.email for u in existing_user):
        raise HTTPException(status_code=400, detail="Email already registered")

    return user_service.create_user(db, user.name, user.email)

@router.get("/", response_model=list[UserResponse])
def list_users(db: Session = Depends(get_db)):
    return user_service.list_users(db)