import logging
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
from app.models.loan import Loan
from app.repositories import loan_repository, book_repository, user_repository

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

class LoanHasMoreThanThreeActiveLoansError(Exception):
    def __init__(self, user_id: int) -> None:
        self.message = f"Cannot create loan for user with ID {user_id}. User has more than 3 active loans."
        super().__init__(self.message)

def create_loan(db: Session, user_id: int, book_id: int) -> Loan:
    book = book_repository.get_book_by_id(db, book_id)
    if book is None:
        logger.warning(f"Attempt to loan non-existent book (ID: {book_id}) by user (ID: {user_id})")

        raise LoanBookNotFoundError(book_id)
    
    if book.is_available is False:
        logger.warning(f"Attempt to loan unavailable book (ID: {book_id}) by user (ID: {user_id})")

        raise LoanBookIsNotAvailableError(book_id)
    
    active_loans = loan_repository.get_active_loans_count_by_user_id(db, user_id)
    if active_loans >= 3:
        logger.warning(f"User (ID: {user_id}) has reached the maximum number of active loans")

        raise LoanHasMoreThanThreeActiveLoansError(user_id)
    
    now = datetime.now(timezone.utc)
    expected_return = now + timedelta(days=14)

    new_loan = Loan(
        user_id=user_id,
        book_id=book_id,
        expected_return_date=expected_return,
        status="active"
    )

    try:
        logger.info(f"Creating loan for user (ID: {user_id}) and book (ID: {book_id})")

        book.is_available = False  # type: ignore[assignment]
        
        db.add(new_loan)
        db.commit()
        db.refresh(new_loan)
    except Exception as e:
        db.rollback()

        logger.error(f"Error while creating loan: {str(e)}", exc_info=True)

        raise e
    
    logger.info(f"Loan created successfully with ID: {new_loan.id} for user (ID: {user_id}) and book (ID: {book_id})")

    return new_loan
    
def list_loans(db: Session, skip: int = 0, limit: int = 100) -> list[Loan]: 
    logger.info(f"Listing loans with skip={skip} and limit={limit}")

    return loan_repository.get_loans(db, skip, limit)

def get_loan_by_id(db: Session, loan_id: int) -> Loan | None:
    logger.info(f"Fetching loan by ID: {loan_id}")

    loan = loan_repository.get_loan_by_id(db, loan_id)

    if not loan:
        logger.warning(f"Loan with ID {loan_id} not found")

        raise LoanNotFoundError(loan_id)
    
    return loan