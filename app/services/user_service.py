from sqlalchemy.orm import Session
from app.repositories import user_repository

def create_user(db: Session, name: str, email: str):
    return user_repository.create_user(db, name, email)

def list_users(db: Session):
    return user_repository.get_users(db)