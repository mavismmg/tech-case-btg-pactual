import logging

from sqlalchemy.orm import Session

from app.core.security import create_access_token, hash_password, verify_password
from app.models.account import Account, AccountRole
from app.repositories import account_repository
from app.schemas.account import AccountBootstrap, AccountCreate, AccountLogin

logger = logging.getLogger(__name__)


class AccountAlreadyExistsError(Exception):
    def __init__(self, email: str):
        self.message = f"Account with email {email} already exists."
        super().__init__(self.message)


class AccountNotFoundError(Exception):
    def __init__(self, account_id: int):
        self.message = f"Account with ID {account_id} not found."
        super().__init__(self.message)


class BootstrapAlreadyUsedError(Exception):
    def __init__(self):
        self.message = "Bootstrap is not available because an account already exists."
        super().__init__(self.message)


class InvalidCredentialsError(Exception):
    def __init__(self):
        self.message = "Invalid email or password."
        super().__init__(self.message)


class InactiveAccountError(Exception):
    def __init__(self):
        self.message = "Account is inactive."
        super().__init__(self.message)


def create_account(db: Session, account_data: AccountCreate) -> Account:
    operation = "create_account"
    existing_account = account_repository.get_account_by_email(db, account_data.email)
    if existing_account:
        logger.warning(
            "Account creation blocked because email already exists",
            extra={"operation": operation, "account_id": existing_account.id, "reason": "email_already_exists"},
        )
        raise AccountAlreadyExistsError(account_data.email)

    account = Account(
        name=account_data.name,
        email=account_data.email,
        password_hash=hash_password(account_data.password),
        role=account_data.role.value,
        is_active=True,
    )

    try:
        created_account = account_repository.create_account(db, account)
        logger.info("Account created successfully", extra={"operation": operation, "account_id": created_account.id})
        return created_account
    except Exception:
        logger.exception("Unexpected error while creating account", extra={"operation": operation})
        raise


def bootstrap_admin(db: Session, account_data: AccountBootstrap) -> Account:
    operation = "bootstrap_admin"
    if account_repository.count_accounts(db) > 0:
        logger.warning(
            "Admin bootstrap blocked because accounts already exist",
            extra={"operation": operation, "reason": "accounts_already_exist"},
        )
        raise BootstrapAlreadyUsedError()

    account = Account(
        name=account_data.name,
        email=account_data.email,
        password_hash=hash_password(account_data.password),
        role=AccountRole.ADMIN.value,
        is_active=True,
    )

    try:
        created_account = account_repository.create_account(db, account)
        logger.info("Admin bootstrapped successfully", extra={"operation": operation, "account_id": created_account.id})
        return created_account
    except Exception:
        logger.exception("Unexpected error while bootstrapping admin", extra={"operation": operation})
        raise


def authenticate_account(db: Session, login_data: AccountLogin) -> Account:
    operation = "authenticate_account"
    account = account_repository.get_account_by_email(db, login_data.email)
    if account is None or not verify_password(login_data.password, account.password_hash):
        logger.warning(
            "Authentication blocked because credentials are invalid",
            extra={"operation": operation, "reason": "invalid_credentials"},
        )
        raise InvalidCredentialsError()

    if not account.is_active:
        logger.warning(
            "Authentication blocked because account is inactive",
            extra={"operation": operation, "account_id": account.id, "reason": "account_inactive"},
        )
        raise InactiveAccountError()

    logger.info("Account authenticated successfully", extra={"operation": operation, "account_id": account.id})
    return account


def create_account_token(account: Account) -> tuple[str, int]:
    return create_access_token(
        subject=str(account.id),
        claims={
            "email": account.email,
            "role": account.role,
        },
    )


def list_accounts(db: Session, skip: int = 0, limit: int = 100) -> tuple[list[Account], int]:
    logger.debug("Listing accounts", extra={"operation": "list_accounts", "skip": skip, "limit": limit})
    return account_repository.get_accounts(db, skip, limit)


def get_account_by_id(db: Session, account_id: int) -> Account:
    operation = "get_account_by_id"
    account = account_repository.get_account_by_id(db, account_id)
    if account is None:
        logger.warning(
            "Account fetch blocked because account was not found",
            extra={"operation": operation, "account_id": account_id, "reason": "account_not_found"},
        )
        raise AccountNotFoundError(account_id)

    return account


def deactivate_account(db: Session, account_id: int) -> Account:
    operation = "deactivate_account"
    account = get_account_by_id(db, account_id)
    try:
        deactivated_account = account_repository.deactivate_account(db, account)
        logger.info("Account deactivated successfully", extra={"operation": operation, "account_id": account_id})
        return deactivated_account
    except AccountNotFoundError:
        raise
    except Exception:
        logger.exception(
            "Unexpected error while deactivating account",
            extra={"operation": operation, "account_id": account_id},
        )
        raise
