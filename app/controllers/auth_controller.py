from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.dependencies import get_current_account, get_db
from app.models.account import Account
from app.schemas.account import AccountBootstrap, AccountLogin, AccountResponse, TokenResponse
from app.services import account_service
from app.services.account_service import (
    BootstrapAlreadyUsedError,
    InactiveAccountError,
    InvalidCredentialsError,
)
from app.core.rate_limit import rate_limit

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post(
    "/bootstrap",
    response_model=AccountResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(rate_limit(limit=5))],
)
def bootstrap_admin(account: AccountBootstrap, db: Session = Depends(get_db)) -> AccountResponse:
    try:
        return account_service.bootstrap_admin(db, account)
    except BootstrapAlreadyUsedError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=e.message,
        )


@router.post(
    "/login",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(rate_limit(limit=10))],
)
def login(login_data: AccountLogin, db: Session = Depends(get_db)) -> TokenResponse:
    try:
        account = account_service.authenticate_account(db, login_data)
    except (InvalidCredentialsError, InactiveAccountError) as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=e.message,
            headers={"WWW-Authenticate": "Bearer"},
        )

    token, expires_in = account_service.create_account_token(account)
    return TokenResponse(
        access_token=token,
        expires_in=expires_in,
        account=AccountResponse.model_validate(account),
    )


@router.get("/me", response_model=AccountResponse, status_code=status.HTTP_200_OK)
def get_me(account: Account = Depends(get_current_account)) -> AccountResponse:
    return account
