import logging

from sqlalchemy.orm import Session

from app.core.security import create_access_token, hash_password, verify_password
from app.models.account import Account, AccountRole
from app.repositories import account_repository
from app.schemas.account import AccountBootstrap, AccountCreate, AccountLogin

logging.basicConfig(level=logging.INFO)
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
    existing_account = account_repository.get_account_by_email(db, account_data.email)
    if existing_account:
        logger.warning("Attempt to create account with existing email: %s", account_data.email)
        raise AccountAlreadyExistsError(account_data.email)

    account = Account(
        name=account_data.name,
        email=account_data.email,
        password_hash=hash_password(account_data.password),
        role=account_data.role.value,
        is_active=True,
    )

    return account_repository.create_account(db, account)


def bootstrap_admin(db: Session, account_data: AccountBootstrap) -> Account:
    if account_repository.count_accounts(db) > 0:
        logger.warning("Attempt to bootstrap admin after accounts already exist")
        raise BootstrapAlreadyUsedError()

    account = Account(
        name=account_data.name,
        email=account_data.email,
        password_hash=hash_password(account_data.password),
        role=AccountRole.ADMIN.value,
        is_active=True,
    )

    return account_repository.create_account(db, account)


def authenticate_account(db: Session, login_data: AccountLogin) -> Account:
    account = account_repository.get_account_by_email(db, login_data.email)
    if account is None or not verify_password(login_data.password, account.password_hash):
        logger.warning("Invalid login attempt for email: %s", login_data.email)
        raise InvalidCredentialsError()

    if not account.is_active:
        logger.warning("Inactive account login attempt: %s", login_data.email)
        raise InactiveAccountError()

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
    return account_repository.get_accounts(db, skip, limit)


def get_account_by_id(db: Session, account_id: int) -> Account:
    account = account_repository.get_account_by_id(db, account_id)
    if account is None:
        raise AccountNotFoundError(account_id)

    return account


def deactivate_account(db: Session, account_id: int) -> Account:
    account = get_account_by_id(db, account_id)
    return account_repository.deactivate_account(db, account)
