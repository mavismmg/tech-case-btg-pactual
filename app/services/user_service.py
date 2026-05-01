import logging

from sqlalchemy.orm import Session
from app.repositories import loan_repository, user_repository
from app.schemas.user import UserCreate, UserUpdate
from app.models.user import User

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
    operation = "create_user"
    existing_user = user_repository.get_user_by_email_including_deleted(db, user_data.email)
    if existing_user and existing_user.deleted_at is None:
        logger.warning(
            "User creation blocked because email already exists",
            extra={"operation": operation, "user_id": existing_user.id, "reason": "email_already_exists"},
        )

        raise UserAlreadyExistsError(user_data.email)
    
    logger.debug("Starting user creation flow", extra={"operation": operation})
    
    try:
        if existing_user:
            new_user = user_repository.restore_user(db, existing_user, user_data)
            logger.info("User restored successfully", extra={"operation": "restore_user", "user_id": new_user.id})
            return new_user

        new_user = user_repository.create_user(db, user_data)
        logger.info("User created successfully", extra={"operation": operation, "user_id": new_user.id})

        return new_user
    except UserAlreadyExistsError:
        raise
    except Exception:
        logger.exception("Unexpected error while creating user", extra={"operation": operation})

        raise

def list_users(db: Session, skip: int = 0, limit: int = 100) -> tuple[list[User], int]:
    logger.debug("Listing users", extra={"operation": "list_users", "skip": skip, "limit": limit})
    
    return user_repository.get_users(db, skip, limit)

def get_user_by_id(db: Session, user_id: int) -> User | None:
    logger.debug("Fetching user by ID", extra={"operation": "get_user_by_id", "user_id": user_id})

    user = user_repository.get_user_by_id(db, user_id)

    if not user:
        logger.warning(
            "User fetch blocked because user was not found",
            extra={"operation": "get_user_by_id", "user_id": user_id, "reason": "user_not_found"},
        )

        raise UserNotFoundError(user_id)
    
    return user

def update_user(db: Session, user_id: int, user_data: UserUpdate) -> User:
    user = get_user_by_id(db, user_id)

    if not user:
        logger.warning(
            "User update blocked because user was not found",
            extra={"operation": "update_user", "user_id": user_id, "reason": "user_not_found"},
        )

        raise UserNotFoundError(user_id)
    
    logger.debug("Starting user update flow", extra={"operation": "update_user", "user_id": user_id})

    try:
        updated_user = user_repository.update_user(db, user, user_data)
        logger.info("User updated successfully", extra={"operation": "update_user", "user_id": user_id})

        return updated_user
    except UserNotFoundError:
        raise
    except Exception:
        logger.exception("Unexpected error while updating user", extra={"operation": "update_user", "user_id": user_id})

        raise
    
def delete_user(db: Session, user_id: int) -> User:
    user = get_user_by_id(db, user_id)

    if not user:
        logger.warning(
            "User deletion blocked because user was not found",
            extra={"operation": "delete_user", "user_id": user_id, "reason": "user_not_found"},
        )

        raise UserNotFoundError(user_id)

    active_loans = loan_repository.get_active_loans_count_by_user_id(db, user_id)
    if active_loans > 0:
        logger.warning(
            "User deletion blocked because user has active loans",
            extra={
                "operation": "delete_user",
                "user_id": user_id,
                "active_loans": active_loans,
                "reason": "active_loans_exist",
            },
        )

        raise UserHasActiveLoansError(user_id)
    
    logger.debug("Starting user deletion flow", extra={"operation": "delete_user", "user_id": user_id})

    try:
        deleted_user = user_repository.soft_delete_user(db, user)
        logger.info("User soft deleted successfully", extra={"operation": "delete_user", "user_id": user_id})

        return deleted_user
    except (UserNotFoundError, UserHasActiveLoansError):
        raise
    except Exception:
        logger.exception("Unexpected error while deleting user", extra={"operation": "delete_user", "user_id": user_id})

        raise
