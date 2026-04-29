import logging

from sqlalchemy.orm import Session
from app.repositories import user_repository
from app.schemas.user import UserCreate
from app.models.user import User

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class UserNotFoundError(Exception):
    def __init__(self, user_id: int):
        self.message = f"User with ID {user_id} not found."
        super().__init__(self.message)

def create_user(db: Session, user_data: UserCreate) -> User:
    logger.info(f"Creating user: {user_data.name} with email {user_data.email}")
    
    try:
        new_user = user_repository.create_user(db, user_data)
        logger.info(f"Successfully created user. ID: {new_user.id}")

        return new_user
    except Exception as e:
        logger.error(f"Failed to create user '{user_data.name}': {str(e)}", exc_info=True)

        raise e

def list_users(db: Session, skip: int = 0, limit: int = 100) -> list[User]:
    logger.info(f"Listing users with skip={skip} and limit={limit}")
    
    return user_repository.get_users(db, skip, limit)

def get_user_by_id(db: Session, user_id: int) -> User | None:
    logger.info(f"Fetching user by ID: {user_id}")

    user = user_repository.get_user_by_id(db, user_id)

    if not user:
        logger.warning(f"User with ID {user_id} not found")

        raise UserNotFoundError(user_id)
    
    return user