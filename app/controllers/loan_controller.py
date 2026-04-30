from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Sequence
from app.dependencies import get_db
from app.dependencies import require_roles
from app.core.rate_limit import rate_limit
from app.models.account import AccountRole
from app.schemas.loan import LoanResponse
from app.schemas.common import PaginatedResponse
from app.services import loan_service
from app.services.loan_service import LoanNotFoundError, LoanBookNotFoundError, LoanBookIsNotAvailableError, LoanLimitExceededError, LoanUserNotFoundError, LoanAlreadyReturnedError 

router = APIRouter(prefix="/loans", tags=["Loans"])
librarian_or_admin = Depends(require_roles(AccountRole.ADMIN, AccountRole.LIBRARIAN))

@router.post(
    "/",
    response_model=LoanResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[librarian_or_admin, Depends(rate_limit(limit=5))],
)
def create_loan(user_id: int, book_id: int, db: Session = Depends(get_db)) -> LoanResponse:
    try:
        return loan_service.create_loan(db, user_id, book_id)
    
    except LoanBookNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message
        )
        
    except LoanUserNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message
        )
        
    except (LoanBookIsNotAvailableError, LoanLimitExceededError) as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=e.message
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while creating the loan."
        )

@router.get("/", response_model=PaginatedResponse[LoanResponse], status_code=status.HTTP_200_OK)
def list_loans(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)) -> PaginatedResponse[LoanResponse]:
    loans, total = loan_service.list_loans(db, skip, limit)
    loan_responses = [LoanResponse.model_validate(loan) for loan in loans]
    return PaginatedResponse(items=loan_responses, total=total, skip=skip, limit=limit)

@router.get("/{loan_id}", response_model=LoanResponse, status_code=status.HTTP_200_OK)
def get_loan(loan_id: int, db: Session = Depends(get_db)) -> LoanResponse:
    try:
        return loan_service.get_loan_by_id(db, loan_id)
    except LoanNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail=e.message
        )

@router.put(
    "/{loan_id}/return",
    response_model=LoanResponse,
    status_code=status.HTTP_200_OK,
    dependencies=[librarian_or_admin, Depends(rate_limit(limit=5))],
)
def return_loan(loan_id: int, db: Session = Depends(get_db)) -> LoanResponse:
    try:
        return loan_service.return_loan(db, loan_id)
    except LoanNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message
        )
    except LoanAlreadyReturnedError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=e.message
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while returning the loan."
        )
