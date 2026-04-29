import logging

from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from app.models.user import User
from app.schemas.user import UserCreate

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_user(db: Session, user_data: UserCreate) -> User:
    user = User(**user_data.model_dump())

    try:
        db.add(user)
        db.commit()
        db.refresh(user)

        logger.info(f"Created user with success: {user.id} - {user.name}")

        return user
    except SQLAlchemyError as e:
        db.rollback()

        logger.error(f"Error while creating user: {str(e)}", exc_info=True)

        raise e

def get_users(db: Session, skip: int = 0, limit: int = 100) -> list[User]:
    logger.info("Fetching users from database")

    return db.query(User).order_by(User.created_at).offset(skip).limit(limit).all()

def get_user_by_id(db: Session, user_id: int) -> User | None:
    logger.info(f"Fetching user by ID: {user_id}")
    
    return db.get(User, user_id)