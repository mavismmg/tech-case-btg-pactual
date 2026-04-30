from datetime import datetime, timezone
import logging

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.models.account import Account

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_account(db: Session, account: Account) -> Account:
    try:
        db.add(account)
        db.commit()
        db.refresh(account)

        logger.info("Created account with success: %s - %s", account.id, account.email)

        return account
    except SQLAlchemyError as e:
        db.rollback()

        logger.error("Error while creating account: %s", str(e), exc_info=True)

        raise e


def get_account_by_email(db: Session, email: str) -> Account | None:
    logger.info("Fetching account by email: %s", email)

    return (
        db.query(Account)
        .filter(Account.email == email, Account.deleted_at.is_(None))
        .first()
    )


def get_account_by_id(db: Session, account_id: int) -> Account | None:
    logger.info("Fetching account by ID: %s", account_id)

    return (
        db.query(Account)
        .filter(Account.id == account_id, Account.deleted_at.is_(None))
        .first()
    )


def count_accounts(db: Session) -> int:
    logger.info("Counting active accounts")

    return db.query(Account).filter(Account.deleted_at.is_(None)).count()


def get_accounts(db: Session, skip: int = 0, limit: int = 100) -> tuple[list[Account], int]:
    logger.info("Fetching accounts from database")

    query = db.query(Account).filter(Account.deleted_at.is_(None))
    total = query.count()
    accounts = query.order_by(Account.created_at).offset(skip).limit(limit).all()
    return accounts, total


def deactivate_account(db: Session, account: Account) -> Account:
    try:
        account.is_active = False
        account.deleted_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(account)

        return account
    except SQLAlchemyError as e:
        db.rollback()

        logger.error("Error while deactivating account: %s", str(e), exc_info=True)

        raise e
