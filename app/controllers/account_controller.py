from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.dependencies import get_db, require_roles
from app.models.account import AccountRole
from app.schemas.account import AccountCreate, AccountResponse
from app.schemas.common import PaginatedResponse
from app.services import account_service
from app.services.account_service import (
    AccountAlreadyExistsError,
    AccountNotFoundError,
    AccountUserNotFoundError,
    ReaderAccountRequiresUserError,
    StaffAccountCannotHaveUserError,
)

router = APIRouter(prefix="/accounts", tags=["Accounts"])

admin_only = Depends(require_roles(AccountRole.ADMIN))


@router.post(
    "/",
    response_model=AccountResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[admin_only],
)
def create_account(account: AccountCreate, db: Session = Depends(get_db)) -> AccountResponse:
    try:
        return account_service.create_account(db, account)
    except AccountAlreadyExistsError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=e.message,
        )
    except AccountUserNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message,
        )
    except (ReaderAccountRequiresUserError, StaffAccountCannotHaveUserError) as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=e.message,
        )


@router.get(
    "/",
    response_model=PaginatedResponse[AccountResponse],
    status_code=status.HTTP_200_OK,
    dependencies=[admin_only],
)
def list_accounts(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)) -> PaginatedResponse[AccountResponse]:
    accounts, total = account_service.list_accounts(db, skip, limit)
    account_responses = [AccountResponse.model_validate(account) for account in accounts]
    return PaginatedResponse(items=account_responses, total=total, skip=skip, limit=limit)


@router.delete(
    "/{account_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[admin_only],
)
def deactivate_account(account_id: int, db: Session = Depends(get_db)) -> None:
    try:
        account_service.deactivate_account(db, account_id)
    except AccountNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message,
        )
