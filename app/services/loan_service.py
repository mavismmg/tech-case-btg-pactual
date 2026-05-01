import logging
from collections.abc import Iterator
from contextlib import ExitStack, contextmanager
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
from app.core.cache import redis_lock
from app.models.loan import Loan, LoanStatus
from app.repositories import loan_repository, book_repository, user_repository
from app.services.book_service import invalidate_available_exemplars_cache

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
        self.message = f"Cannot create loan for user with ID {user_id}. User already has 3 active loans."
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


class LoanRenewalNotAllowedError(Exception):
    def __init__(self, loan_id: int, reason: str) -> None:
        self.message = f"Cannot renew loan with ID {loan_id}. {reason}"
        super().__init__(self.message)


BUSINESS_RULE_EXCEPTIONS = (
    LoanNotFoundError,
    LoanBookNotFoundError,
    LoanBookIsNotAvailableError,
    LoanLimitExceededError,
    LoanUserNotFoundError,
    LoanAlreadyReturnedError,
    LoanReturnBookNotFoundError,
    LoanRenewalNotAllowedError,
)


def _loan_user_lock_key(user_id: int) -> str:
    return f"loans:create:user:{user_id}"


def _loan_book_lock_key(book_id: int) -> str:
    return f"loans:create:book:{book_id}"


@contextmanager
def _transaction(db: Session) -> Iterator[None]:
    if db.in_transaction():
        try:
            yield
            db.commit()
        except Exception:
            db.rollback()
            raise
        return

    with db.begin():
        yield


def create_loan(db: Session, user_id: int, book_id: int) -> Loan:
    operation = "create_loan"
    logger.debug(
        "Starting loan creation flow",
        extra={"operation": operation, "user_id": user_id, "book_id": book_id},
    )

    book_isbn = None

    try:
        with ExitStack() as stack:
            stack.enter_context(redis_lock(_loan_user_lock_key(user_id)))
            stack.enter_context(redis_lock(_loan_book_lock_key(book_id)))

            with _transaction(db):
                user = user_repository.get_user_by_id(db, user_id)
                if user is None:
                    logger.warning(
                        "Loan creation blocked because user was not found",
                        extra={
                            "operation": operation,
                            "user_id": user_id,
                            "book_id": book_id,
                            "reason": "user_not_found",
                        },
                    )
                    raise LoanUserNotFoundError(user_id)
                
                active_loans = loan_repository.get_active_loans_count_by_user_id(db, user_id)
                if active_loans >= 3:
                    logger.warning(
                        "Loan creation blocked because user reached the active loan limit",
                        extra={
                            "operation": operation,
                            "user_id": user_id,
                            "book_id": book_id,
                            "active_loans": active_loans,
                            "limit": 3,
                            "reason": "active_loan_limit_reached",
                        },
                    )
                    raise LoanLimitExceededError(user_id)
                
                now = datetime.now(timezone.utc)
                expected_return = now + timedelta(days=14)

                new_loan = Loan(
                    user_id=user_id,
                    book_id=book_id,
                    expected_return_date=expected_return,
                    status=LoanStatus.ACTIVE
                )

                logger.debug(
                    "Creating loan record inside transaction",
                    extra={"operation": operation, "user_id": user_id, "book_id": book_id},
                )
                book = book_repository.get_book_by_id(db, book_id)
                if book is None:
                    logger.warning(
                        "Loan creation blocked because book was not found",
                        extra={
                            "operation": operation,
                            "user_id": user_id,
                            "book_id": book_id,
                            "reason": "book_not_found",
                        },
                    )
                    raise LoanBookNotFoundError(book_id)
                
                if not book.is_available:
                    logger.warning(
                        "Loan creation blocked because book is not available",
                        extra={
                            "operation": operation,
                            "user_id": user_id,
                            "book_id": book_id,
                            "reason": "book_not_available",
                        },
                    )
                    raise LoanBookIsNotAvailableError(book_id)
                
                book_isbn = book.isbn
                book.is_available = False
                db.add(new_loan)

        if book_isbn is not None:
            invalidate_available_exemplars_cache(book_isbn)
        db.refresh(new_loan)
    except BUSINESS_RULE_EXCEPTIONS:
        db.rollback()
        raise
    except Exception:
        db.rollback()

        logger.exception(
            "Unexpected error while creating loan",
            extra={"operation": operation, "user_id": user_id, "book_id": book_id},
        )

        raise
    
    logger.info(
        "Loan created successfully",
        extra={"operation": operation, "user_id": user_id, "book_id": book_id, "loan_id": new_loan.id},
    )

    return new_loan

def return_loan(db: Session, loan_id: int) -> Loan:
    operation = "return_loan"
    logger.debug("Starting loan return flow", extra={"operation": operation, "loan_id": loan_id})

    book_isbn = None

    try:
        with _transaction(db):
            loan = loan_repository.get_loan_by_id(db, loan_id)

            if loan is None:
                logger.warning(
                    "Loan return blocked because loan was not found",
                    extra={"operation": operation, "loan_id": loan_id, "reason": "loan_not_found"},
                )
                raise LoanNotFoundError(loan_id)
            
            if loan.status != LoanStatus.ACTIVE:
                logger.warning(
                    "Loan return blocked because loan is not active",
                    extra={"operation": operation, "loan_id": loan_id, "reason": "loan_not_active"},
                )
                raise LoanAlreadyReturnedError(loan_id)
            
            now = datetime.now(timezone.utc)
            days_overdue = max(0, (now - loan.expected_return_date).days)
            loan.fine_value = days_overdue * 2.0
            loan.actual_return_date = now
            loan.status = LoanStatus.RETURNED
            
            book = book_repository.get_book_by_id(db, loan.book_id)
            if book is None:
                logger.warning(
                    "Loan return blocked because related book was not found",
                    extra={
                        "operation": operation,
                        "loan_id": loan_id,
                        "book_id": loan.book_id,
                        "user_id": loan.user_id,
                        "reason": "book_not_found",
                    },
                )
                raise LoanReturnBookNotFoundError(loan.book_id)
            
            book.is_available = True
            book_isbn = book.isbn
            logger.debug(
                "Applying loan return changes inside transaction",
                extra={
                    "operation": operation,
                    "loan_id": loan_id,
                    "book_id": loan.book_id,
                    "user_id": loan.user_id,
                    "fine_value": loan.fine_value,
                },
            )

        if book_isbn is not None:
            invalidate_available_exemplars_cache(book_isbn)
        db.refresh(loan)
    except BUSINESS_RULE_EXCEPTIONS:
        db.rollback()
        raise
    except Exception:
        db.rollback()

        logger.exception(
            "Unexpected error while returning loan",
            extra={"operation": operation, "loan_id": loan_id},
        )

        raise
    
    logger.info(
        "Loan returned successfully",
        extra={
            "operation": operation,
            "loan_id": loan.id,
            "user_id": loan.user_id,
            "book_id": loan.book_id,
            "fine_value": loan.fine_value,
        },
    )

    return loan


def renew_loan(db: Session, loan_id: int) -> Loan:
    operation = "renew_loan"
    logger.debug("Starting loan renewal flow", extra={"operation": operation, "loan_id": loan_id})

    try:
        with _transaction(db):
            loan = loan_repository.get_loan_by_id(db, loan_id)
            if loan is None:
                logger.warning(
                    "Loan renewal blocked because loan was not found",
                    extra={"operation": operation, "loan_id": loan_id, "reason": "loan_not_found"},
                )
                raise LoanNotFoundError(loan_id)

            if loan.status != LoanStatus.ACTIVE:
                logger.warning(
                    "Loan renewal blocked because loan is not active",
                    extra={"operation": operation, "loan_id": loan_id, "reason": "loan_not_active"},
                )
                raise LoanRenewalNotAllowedError(loan_id, "Loan is not active.")

            now = datetime.now(timezone.utc)
            expected_return_date = loan.expected_return_date
            if expected_return_date.tzinfo is None:
                expected_return_date = expected_return_date.replace(tzinfo=timezone.utc)

            if expected_return_date < now:
                logger.warning(
                    "Loan renewal blocked because loan is overdue",
                    extra={"operation": operation, "loan_id": loan_id, "reason": "loan_overdue"},
                )
                raise LoanRenewalNotAllowedError(loan_id, "Loan is overdue.")

            if loan.renewal_count >= 1:
                logger.warning(
                    "Loan renewal blocked because renewal limit was reached",
                    extra={
                        "operation": operation,
                        "loan_id": loan_id,
                        "renewal_count": loan.renewal_count,
                        "reason": "renewal_limit_reached",
                    },
                )
                raise LoanRenewalNotAllowedError(loan_id, "Renewal limit reached.")

            loan.expected_return_date = loan.expected_return_date + timedelta(days=14)
            loan.renewal_count += 1

        db.refresh(loan)
    except BUSINESS_RULE_EXCEPTIONS:
        db.rollback()
        raise
    except Exception:
        db.rollback()
        logger.exception("Unexpected error while renewing loan", extra={"operation": operation, "loan_id": loan_id})
        raise

    logger.info(
        "Loan renewed successfully",
        extra={
            "operation": operation,
            "loan_id": loan.id,
            "user_id": loan.user_id,
            "book_id": loan.book_id,
            "renewal_count": loan.renewal_count,
        },
    )

    return loan
    
def get_loans_by_user(db: Session, user_id: int, skip: int = 0, limit: int = 100) -> tuple[list[Loan], int]:
    logger.debug("Fetching loans for user", extra={"operation": "get_loans_by_user", "user_id": user_id})
    loans, total = loan_repository.get_loans_by_user_id(db, user_id, skip, limit)
    return loans, total
    
def list_loans(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    status: LoanStatus | None = None,
    user_id: int | None = None,
    overdue: bool | None = None,
) -> tuple[list[Loan], int]:
    logger.debug(
        "Listing loans",
        extra={
            "operation": "list_loans",
            "skip": skip,
            "limit": limit,
            "status": status.value if status else None,
            "user_id": user_id,
            "overdue": overdue,
        },
    )

    return loan_repository.get_loans(db, skip, limit, status, user_id, overdue)

def list_active_loans(db: Session, skip: int = 0, limit: int = 100) -> tuple[list[Loan], int]:
    return list_loans(db, skip=skip, limit=limit, status=LoanStatus.ACTIVE)

def list_overdue_loans(db: Session, skip: int = 0, limit: int = 100) -> tuple[list[Loan], int]:
    return list_loans(db, skip=skip, limit=limit, overdue=True)

def get_loan_by_id(db: Session, loan_id: int) -> Loan | None:
    logger.debug("Fetching loan by ID", extra={"operation": "get_loan_by_id", "loan_id": loan_id})

    loan = loan_repository.get_loan_by_id(db, loan_id)

    if not loan:
        logger.warning(
            "Loan fetch blocked because loan was not found",
            extra={"operation": "get_loan_by_id", "loan_id": loan_id, "reason": "loan_not_found"},
        )

        raise LoanNotFoundError(loan_id)
    
    return loan
