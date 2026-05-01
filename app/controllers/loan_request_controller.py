from typing import NoReturn

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.dependencies import get_current_account, get_db, require_roles
from app.models.account import Account, AccountRole
from app.models.loan_request import LoanRequestStatus, LoanRequestType
from app.schemas.common import PaginatedResponse
from app.schemas.loan_request import (
    LoanActionRequestCreate,
    LoanRequestCreate,
    LoanRequestReject,
    LoanRequestResponse,
)
from app.services import loan_request_service
from app.services.loan_request_service import (
    DuplicatePendingLoanRequestError,
    LoanRequestAlreadyReviewedError,
    LoanRequestApprovalError,
    LoanRequestBookNotFoundError,
    LoanRequestLoanNotFoundError,
    LoanRequestNotFoundError,
    LoanRequestOwnershipError,
    ReaderAccountMissingUserError,
    ReaderAccountRequiredError,
)

router = APIRouter(tags=["Loan Requests"])
staff_only = Depends(require_roles(AccountRole.ADMIN, AccountRole.LIBRARIAN))


def _raise_request_error(exc: Exception) -> NoReturn:
    if isinstance(exc, (LoanRequestBookNotFoundError, LoanRequestLoanNotFoundError, LoanRequestNotFoundError)):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=exc.message)

    if isinstance(exc, (ReaderAccountRequiredError, ReaderAccountMissingUserError)):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=exc.message)

    if isinstance(
        exc,
        (
            DuplicatePendingLoanRequestError,
            LoanRequestAlreadyReviewedError,
            LoanRequestApprovalError,
            LoanRequestOwnershipError,
        ),
    ):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=exc.message)

    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="An unexpected error occurred while processing the loan request.",
    )


@router.post(
    "/loan-requests/",
    response_model=LoanRequestResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_loan_request(
    request_data: LoanRequestCreate,
    account: Account = Depends(get_current_account),
    db: Session = Depends(get_db),
) -> LoanRequestResponse:
    try:
        return loan_request_service.create_loan_request(db, account, request_data.book_id)
    except Exception as exc:
        _raise_request_error(exc)


@router.post(
    "/return-requests/",
    response_model=LoanRequestResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_return_request(
    request_data: LoanActionRequestCreate,
    account: Account = Depends(get_current_account),
    db: Session = Depends(get_db),
) -> LoanRequestResponse:
    try:
        return loan_request_service.create_loan_action_request(
            db,
            account,
            request_data.loan_id,
            LoanRequestType.RETURN,
        )
    except Exception as exc:
        _raise_request_error(exc)


@router.post(
    "/renewal-requests/",
    response_model=LoanRequestResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_renewal_request(
    request_data: LoanActionRequestCreate,
    account: Account = Depends(get_current_account),
    db: Session = Depends(get_db),
) -> LoanRequestResponse:
    try:
        return loan_request_service.create_loan_action_request(
            db,
            account,
            request_data.loan_id,
            LoanRequestType.RENEWAL,
        )
    except Exception as exc:
        _raise_request_error(exc)


@router.get(
    "/loan-requests/",
    response_model=PaginatedResponse[LoanRequestResponse],
    status_code=status.HTTP_200_OK,
    dependencies=[staff_only],
)
def list_loan_requests(
    status_filter: LoanRequestStatus | None = Query(None, alias="status"),
    type_filter: LoanRequestType | None = Query(None, alias="type"),
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
) -> PaginatedResponse[LoanRequestResponse]:
    requests, total = loan_request_service.list_loan_requests(db, status_filter, type_filter, skip, limit)
    request_responses = [LoanRequestResponse.model_validate(loan_request) for loan_request in requests]
    return PaginatedResponse(items=request_responses, total=total, skip=skip, limit=limit)


@router.post(
    "/loan-requests/{request_id}/approve",
    response_model=LoanRequestResponse,
    status_code=status.HTTP_200_OK,
    dependencies=[staff_only],
)
def approve_loan_request(
    request_id: int,
    reviewer_account: Account = Depends(get_current_account),
    db: Session = Depends(get_db),
) -> LoanRequestResponse:
    try:
        return loan_request_service.approve_loan_request(db, request_id, reviewer_account)
    except Exception as exc:
        _raise_request_error(exc)


@router.post(
    "/loan-requests/{request_id}/reject",
    response_model=LoanRequestResponse,
    status_code=status.HTTP_200_OK,
    dependencies=[staff_only],
)
def reject_loan_request(
    request_id: int,
    request_data: LoanRequestReject,
    reviewer_account: Account = Depends(get_current_account),
    db: Session = Depends(get_db),
) -> LoanRequestResponse:
    try:
        return loan_request_service.reject_loan_request(db, request_id, reviewer_account, request_data.reason)
    except Exception as exc:
        _raise_request_error(exc)
