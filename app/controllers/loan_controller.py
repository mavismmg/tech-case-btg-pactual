from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Sequence
from app.core.database import SessionLocal
from app.schemas.loan import LoanResponse
from app.services import loan_service
from app.services.loan_service import LoanNotFoundError, LoanBookNotFoundError, LoanBookIsNotAvailableError, LoanHasMoreThanThreeActiveLoansError 

router = APIRouter(prefix="/loans", tags=["Loans"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/", response_model=LoanResponse, status_code=status.HTTP_201_CREATED)
def create_loan(user_id: int, book_id: int, db: Session = Depends(get_db)) -> LoanResponse:
    try:
        return loan_service.create_loan(db, user_id, book_id)
    
    except LoanBookNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message
        )
        
    except (LoanBookIsNotAvailableError, LoanHasMoreThanThreeActiveLoansError) as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=e.message
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ocorreu um erro interno ao processar o empréstimo."
        )

@router.get("/", response_model=list[LoanResponse], status_code=status.HTTP_200_OK)
def list_loans(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)) -> Sequence[LoanResponse]:
    return loan_service.list_loans(db, skip, limit)

@router.get("/{loan_id}", response_model=LoanResponse, status_code=status.HTTP_200_OK)
def get_loan(loan_id: int, db: Session = Depends(get_db)) -> LoanResponse:
    try:
        return loan_service.get_loan_by_id(db, loan_id)
    except LoanNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail=e.message
        )