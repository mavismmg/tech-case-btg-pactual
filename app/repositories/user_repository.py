from datetime import datetime, timezone
import logging

from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate

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

def get_users(db: Session, skip: int = 0, limit: int = 100) -> tuple[list[User], int]:
    logger.info("Fetching users from database")

    query = db.query(User).filter(User.deleted_at.is_(None))
    total = query.count()
    users = query.order_by(User.created_at).offset(skip).limit(limit).all()
    return users, total

def get_user_by_id(db: Session, user_id: int) -> User | None:
    logger.info(f"Fetching user by ID: {user_id}")
    
    return db.query(User).filter(User.id == user_id, User.deleted_at.is_(None)).with_for_update(of=User).first()

def get_user_by_email(db: Session, email: str) -> User | None:
    logger.info(f"Fetching user by email: {email}")

    return db.query(User).filter(User.email == email, User.deleted_at.is_(None)).first()

def get_user_by_email_including_deleted(db: Session, email: str) -> User | None:
    logger.info(f"Fetching user by email including deleted: {email}")

    return db.query(User).filter(User.email == email).with_for_update(of=User).first()

def update_user(db: Session, db_user: User, user_data: UserUpdate) -> User:
    updated_data = user_data.model_dump(exclude_unset=True)

    for key, value in updated_data.items():
        setattr(db_user, key, value)

    try:
        db.commit()
        db.refresh(db_user)

        return db_user
    except SQLAlchemyError as e:
        db.rollback()

        logger.error(f"Error while updating user: {str(e)}", exc_info=True)

        raise e

def restore_user(db: Session, db_user: User, user_data: UserCreate) -> User:
    try:
        db_user.name = user_data.name
        db_user.email = user_data.email
        db_user.deleted_at = None
        db_user.is_active = True

        db.commit()
        db.refresh(db_user)

        return db_user
    except SQLAlchemyError as e:
        db.rollback()

        logger.error(f"Error while restoring user: {str(e)}", exc_info=True)

        raise e
    
def soft_delete_user(db: Session, db_user: User) -> User:
    try:
        db_user.deleted_at = datetime.now(timezone.utc)
        db_user.is_active = False

        db.commit()
        db.refresh(db_user)

        return db_user
    except SQLAlchemyError as e:
        db.rollback()

        logger.error(f"Error while soft deleting user: {str(e)}", exc_info=True)

        raise e
