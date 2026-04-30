import logging

from sqlalchemy.orm import Session
from app.repositories import loan_repository, user_repository
from app.schemas.user import UserCreate, UserUpdate
from app.models.user import User

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class UserNotFoundError(Exception):
    def __init__(self, user_id: int):
        self.message = f"User with ID {user_id} not found."
        super().__init__(self.message)

class UserAlreadyExistsError(Exception):
    def __init__(self, email: str):
        self.message = f"User with email {email} already exists."
        super().__init__(self.message)

class UserHasActiveLoansError(Exception):
    def __init__(self, user_id: int):
        self.message = f"Cannot delete user with ID {user_id}. User has active loans."
        super().__init__(self.message)

def create_user(db: Session, user_data: UserCreate) -> User:
    existing_user = user_repository.get_user_by_email(db, user_data.email)
    if existing_user:
        logger.warning(f"Attempt to create user with existing email: {user_data.email}")

        raise UserAlreadyExistsError(user_data.email)
    
    logger.info(f"Creating user: {user_data.name} with email {user_data.email}")
    
    try:
        new_user = user_repository.create_user(db, user_data)
        logger.info(f"Successfully created user. ID: {new_user.id}")

        return new_user
    except Exception as e:
        logger.error(f"Failed to create user '{user_data.name}': {str(e)}", exc_info=True)

        raise e

def list_users(db: Session, skip: int = 0, limit: int = 100) -> tuple[list[User], int]:
    logger.info(f"Listing users with skip={skip} and limit={limit}")
    
    return user_repository.get_users(db, skip, limit)

def get_user_by_id(db: Session, user_id: int) -> User | None:
    logger.info(f"Fetching user by ID: {user_id}")

    user = user_repository.get_user_by_id(db, user_id)

    if not user:
        logger.warning(f"User with ID {user_id} not found")

        raise UserNotFoundError(user_id)
    
    return user

def update_user(db: Session, user_id: int, user_data: UserUpdate) -> User:
    user = get_user_by_id(db, user_id)

    if not user:
        logger.warning(f"User with ID {user_id} not found for update")

        raise UserNotFoundError(user_id)
    
    logger.info(f"Updating user with ID {user_id}")

    try:
        updated_user = user_repository.update_user(db, user, user_data)
        logger.info(f"Successfully updated user with ID {user_id}")

        return updated_user
    except Exception as e:
        logger.error(f"Failed to update user with ID {user_id}: {str(e)}", exc_info=True)

        raise e
    
def delete_user(db: Session, user_id: int) -> User:
    user = get_user_by_id(db, user_id)

    if not user:
        logger.warning(f"User with ID {user_id} not found for deletion")

        raise UserNotFoundError(user_id)

    active_loans = loan_repository.get_active_loans_count_by_user_id(db, user_id)
    if active_loans > 0:
        logger.warning(f"Attempt to delete user with active loans. User ID: {user_id}")

        raise UserHasActiveLoansError(user_id)
    
    logger.info(f"Soft deleting user with ID {user_id}")

    try:
        deleted_user = user_repository.soft_delete_user(db, user)
        logger.info(f"Successfully soft deleted user with ID {user_id}")

        return deleted_user
    except Exception as e:
        logger.error(f"Failed to delete user with ID {user_id}: {str(e)}", exc_info=True)

        raise e
