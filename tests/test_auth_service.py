import pytest

from app.core.security import hash_password, verify_password
from app.models.account import AccountRole
from app.schemas.account import AccountBootstrap, AccountLogin
from app.services.account_service import (
    BootstrapAlreadyUsedError,
    InvalidCredentialsError,
    authenticate_account,
    bootstrap_admin,
    create_account_token,
)


def test_hash_and_verify_password():
    password_hash = hash_password("strong-password")

    assert password_hash != "strong-password"
    assert verify_password("strong-password", password_hash)
    assert not verify_password("wrong-password", password_hash)


def test_bootstrap_admin_creates_first_account(db):
    account = bootstrap_admin(
        db,
        AccountBootstrap(
            name="Admin",
            email="admin@example.com",
            password="strong-password",
        ),
    )

    assert account.id is not None
    assert account.role == AccountRole.ADMIN
    assert account.is_active is True


def test_bootstrap_admin_only_once(db):
    bootstrap_admin(
        db,
        AccountBootstrap(
            name="Admin",
            email="admin@example.com",
            password="strong-password",
        ),
    )

    with pytest.raises(BootstrapAlreadyUsedError):
        bootstrap_admin(
            db,
            AccountBootstrap(
                name="Second Admin",
                email="admin2@example.com",
                password="strong-password",
            ),
        )


def test_login_valid_credentials_returns_account(db):
    account = bootstrap_admin(
        db,
        AccountBootstrap(
            name="Admin",
            email="admin@example.com",
            password="strong-password",
        ),
    )

    authenticated_account = authenticate_account(
        db,
        AccountLogin(email="admin@example.com", password="strong-password"),
    )

    assert authenticated_account.id == account.id


def test_login_invalid_credentials_raises(db):
    bootstrap_admin(
        db,
        AccountBootstrap(
            name="Admin",
            email="admin@example.com",
            password="strong-password",
        ),
    )

    with pytest.raises(InvalidCredentialsError):
        authenticate_account(
            db,
            AccountLogin(email="admin@example.com", password="wrong-password"),
        )


def test_create_token_for_account(db):
    account = bootstrap_admin(
        db,
        AccountBootstrap(
            name="Admin",
            email="admin@example.com",
            password="strong-password",
        ),
    )

    token, expires_in = create_account_token(account)

    assert token
    assert expires_in > 0
