import logging
from contextlib import ExitStack
from typing import ContextManager
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
from app.core.cache import redis_lock
from app.models.loan import Loan, LoanStatus
from app.repositories import loan_repository, book_repository, user_repository
from app.services.book_service import invalidate_available_exemplars_cache

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class LoanNotFoundError(Exception):
    def __init__(self, loan_id: int) -> None:
        self.message = f"Loan with ID {loan_id} not found."
        super().__init__(self.message)

class LoanBookNotFoundError(Exception):
    def __init__(self, book_id: int) -> None:
        self.message = f"Cannot create loan for book with ID {book_id}. Book do not exist."
        super().__init__(self.message)

class LoanBookIsNotAvailableError(Exception):
    def __init__(self, book_id: int) -> None:
        self.message = f"Cannot create loan for book with ID {book_id}. Book is not available."
        super().__init__(self.message)

class LoanLimitExceededError(Exception):
    def __init__(self, user_id: int) -> None:
        self.message = f"Cannot create loan for user with ID {user_id}. User has more than 3 active loans."
        super().__init__(self.message)

class LoanUserNotFoundError(Exception):
    def __init__(self, user_id: int) -> None:
        self.message = f"Cannot create loan for user with ID {user_id}. User does not exist."
        super().__init__(self.message)

class LoanAlreadyReturnedError(Exception):
    def __init__(self, loan_id: int) -> None:
        self.message = f"Loan with ID {loan_id} has already been returned."
        super().__init__(self.message)

class LoanReturnBookNotFoundError(Exception):
    def __init__(self, book_id: int) -> None:
        self.message = f"Cannot return loan for book with ID {book_id}. Book does not exist."
        super().__init__(self.message)


def _loan_user_lock_key(user_id: int) -> str:
    return f"loans:create:user:{user_id}"


def _loan_book_lock_key(book_id: int) -> str:
    return f"loans:create:book:{book_id}"


def _transaction(db: Session) -> ContextManager:
    if db.in_transaction():
        return db.begin_nested()

    return db.begin()


def create_loan(db: Session, user_id: int, book_id: int) -> Loan:
    logger.info(f"Attempting to create loan for user (ID: {user_id}) and book (ID: {book_id})")

    book_isbn = None

    try:
        with ExitStack() as stack:
            stack.enter_context(redis_lock(_loan_user_lock_key(user_id)))
            stack.enter_context(redis_lock(_loan_book_lock_key(book_id)))

            with _transaction(db):
                user = user_repository.get_user_by_id(db, user_id)
                if user is None:
                    logger.warning(f"Attempt to create loan for non-existent user (ID: {user_id})")
                    raise LoanUserNotFoundError(user_id)
                
                active_loans = loan_repository.get_active_loans_count_by_user_id(db, user_id)
                if active_loans >= 3:
                    logger.warning(f"User (ID: {user_id}) has reached the maximum number of active loans")

                    raise LoanLimitExceededError(user_id)
                
                now = datetime.now(timezone.utc)
                expected_return = now + timedelta(days=14)

                new_loan = Loan(
                    user_id=user_id,
                    book_id=book_id,
                    expected_return_date=expected_return,
                    status=LoanStatus.ACTIVE
                )

            
                logger.info(f"Creating loan for user (ID: {user_id}) and book (ID: {book_id})")

            
                book = book_repository.get_book_by_id(db, book_id)
                if book is None:
                    logger.warning(f"Book with ID {book_id} not found during loan creation for user (ID: {user_id})")
                    
                    raise LoanBookNotFoundError(book_id)
                
                if not book.is_available:
                    logger.warning(f"Book with ID {book_id} is not available during loan creation for user (ID: {user_id})")
                    
                    raise LoanBookIsNotAvailableError(book_id)
                
                book_isbn = book.isbn
                book.is_available = False
                db.add(new_loan)

        if book_isbn is not None:
            invalidate_available_exemplars_cache(book_isbn)
        db.refresh(new_loan)
    except Exception as e:
        db.rollback()

        logger.error(f"Error while creating loan: {str(e)}", exc_info=True)

        raise
    
    logger.info(f"Loan created successfully with ID: {new_loan.id} for user (ID: {user_id}) and book (ID: {book_id})")

    return new_loan

def return_loan(db: Session, loan_id: int) -> Loan:
    logger.info(f"Attempting to return loan with ID: {loan_id}")

    book_isbn = None

    try:
        with _transaction(db):
            loan = loan_repository.get_loan_by_id(db, loan_id)

            if loan is None:
                logger.warning(f"Attempt to return non-existent loan (ID: {loan_id})")

                raise LoanNotFoundError(loan_id)
            
            if loan.status != LoanStatus.ACTIVE:
                logger.warning(f"Attempt to return already returned loan (ID: {loan_id})")

                raise LoanAlreadyReturnedError(loan_id)
            
            now = datetime.now(timezone.utc)
            days_overdue = max(0, (now - loan.expected_return_date).days)
            loan.fine_value = days_overdue * 2.0
            loan.actual_return_date = now
            loan.status = LoanStatus.RETURNED
            
            book = book_repository.get_book_by_id(db, loan.book_id)
            if book is None:
                logger.warning(f"Book with ID {loan.book_id} not found during loan return for loan (ID: {loan_id})")
                
                raise LoanReturnBookNotFoundError(loan.book_id)
            
            book.is_available = True
            book_isbn = book.isbn
            
            logger.info(f"Returning loan (ID: {loan_id}) with fine R$ {loan.fine_value}")

        if book_isbn is not None:
            invalidate_available_exemplars_cache(book_isbn)
        db.refresh(loan)
    except Exception as e:
        db.rollback()

        logger.error(f"Error while returning loan (ID: {loan_id}): {str(e)}", exc_info=True)

        raise
    
    logger.info(f"Loan (ID: {loan_id}) returned successfully")

    return loan
    
def get_loans_by_user(db: Session, user_id: int, skip: int = 0, limit: int = 100) -> tuple[list[Loan], int]:
    logger.info(f"Fetching loans for user ID: {user_id}")
    loans, total = loan_repository.get_loans_by_user_id(db, user_id, skip, limit)
    return loans, total
    
def list_loans(db: Session, skip: int = 0, limit: int = 100) -> tuple[list[Loan], int]:
    logger.info(f"Listing loans with skip={skip} and limit={limit}")

    return loan_repository.get_loans(db, skip, limit)

def get_loan_by_id(db: Session, loan_id: int) -> Loan | None:
    logger.info(f"Fetching loan by ID: {loan_id}")

    loan = loan_repository.get_loan_by_id(db, loan_id)

    if not loan:
        logger.warning(f"Loan with ID {loan_id} not found")

        raise LoanNotFoundError(loan_id)
    
    return loan
