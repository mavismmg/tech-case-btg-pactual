from typing import Sequence
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.dependencies import get_db
from app.schemas.user import UserCreate, UserUpdate, UserResponse
from app.schemas.loan import LoanResponse
from app.schemas.common import PaginatedResponse
from app.services import user_service, loan_service
from app.services.user_service import UserNotFoundError, UserAlreadyExistsError

router = APIRouter(prefix="/users", tags=["Users"])

@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(user: UserCreate, db: Session = Depends(get_db)) -> UserResponse:
    try:
        return user_service.create_user(db, user)
    except UserAlreadyExistsError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=e.message
        )

@router.get("/", response_model=PaginatedResponse[UserResponse], status_code=status.HTTP_200_OK)
def list_users(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)) -> PaginatedResponse[UserResponse]:
    users, total = user_service.list_users(db, skip, limit)
    user_responses = [UserResponse.model_validate(user) for user in users]
    return PaginatedResponse(items=user_responses, total=total, skip=skip, limit=limit)

@router.get("/{user_id}", response_model=UserResponse, status_code=status.HTTP_200_OK)
def get_user(user_id: int, db: Session = Depends(get_db)) -> UserResponse:
    try:
        return user_service.get_user_by_id(db, user_id)
    except UserNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail=e.message
        )

@router.put("/{user_id}", response_model=UserResponse, status_code=status.HTTP_200_OK)
def update_user(user_id: int, user_data: UserUpdate, db: Session = Depends(get_db)) -> UserResponse:
    try:
        return user_service.update_user(db, user_id, user_data)
    except UserNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail=e.message
        )
    
@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(user_id: int, db: Session = Depends(get_db)) -> None:
    try:
        user_service.delete_user(db, user_id)
    except UserNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail=e.message
        )

@router.get("/{user_id}/loans", response_model=PaginatedResponse[LoanResponse], status_code=status.HTTP_200_OK)
def get_user_loans(user_id: int, skip: int = 0, limit: int = 100, db: Session = Depends(get_db)) -> PaginatedResponse[LoanResponse]:
    try:
        loans, total = loan_service.get_loans_by_user(db, user_id, skip, limit)
        loan_responses = [LoanResponse.model_validate(loan) for loan in loans]
        return PaginatedResponse(items=loan_responses, total=total, skip=skip, limit=limit)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while fetching user loans."
        )