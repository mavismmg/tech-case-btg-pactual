from sqlalchemy.orm import Session, joinedload
from sqlalchemy.exc import SQLAlchemyError
from app.models.loan import Loan
from app.schemas.loan import LoanCreate

import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_loan(db: Session, loan_data: LoanCreate) -> Loan:
    db_loan = Loan(**loan_data.model_dump())

    try:
        db.add(db_loan)
        db.commit()
        db.refresh(db_loan)

        logger.info(f"Created loan with success: {db_loan.id} - User ID: {db_loan.user_id}, Book ID: {db_loan.book_id}")

        return db_loan
    except SQLAlchemyError as e:
        db.rollback()

        logger.error(f"Error while creating loan: {str(e)}", exc_info=True)

        raise e
    
def get_loans(db: Session, skip: int = 0, limit: int = 100) -> list[Loan]:
    logger.info("Fetching loans from database")
    
    return (
        db.query(Loan)
        .options(joinedload(Loan.user), joinedload(Loan.book))
        .order_by(Loan.loan_date)
        .offset(skip)
        .limit(limit)
        .all()
    )

def get_loan_by_id(db: Session, loan_id: int) -> Loan | None:
    logger.info(f"Fetching loan with ID: {loan_id}")

    return (
        db.query(Loan)
        .options(joinedload(Loan.user), joinedload(Loan.book))
        .filter(Loan.id == loan_id)
        .one_or_none()
    )

def get_active_loans_count_by_user_id(db: Session, user_id: int) -> int:
    logger.info(f"Counting active loans for user ID: {user_id}")

    return db.query(Loan).filter(Loan.user_id == user_id, Loan.status == "active").count()