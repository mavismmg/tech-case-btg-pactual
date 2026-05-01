from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.loan_request import LoanRequest, LoanRequestStatus, LoanRequestType


def create_loan_request(db: Session, loan_request: LoanRequest) -> LoanRequest:
    db.add(loan_request)
    db.commit()
    db.refresh(loan_request)
    return loan_request


def get_loan_request_by_id(db: Session, request_id: int) -> LoanRequest | None:
    return (
        db.query(LoanRequest)
        .filter(LoanRequest.id == request_id)
        .with_for_update(of=LoanRequest)
        .first()
    )


def get_pending_loan_request_by_user_and_book(
    db: Session,
    user_id: int,
    book_id: int,
) -> LoanRequest | None:
    return (
        db.query(LoanRequest)
        .filter(
            LoanRequest.request_type == LoanRequestType.LOAN.value,
            LoanRequest.status == LoanRequestStatus.PENDING.value,
            LoanRequest.user_id == user_id,
            LoanRequest.book_id == book_id,
        )
        .first()
    )


def get_pending_loan_request_by_type_and_loan(
    db: Session,
    request_type: LoanRequestType,
    loan_id: int,
) -> LoanRequest | None:
    return (
        db.query(LoanRequest)
        .filter(
            LoanRequest.request_type == request_type.value,
            LoanRequest.status == LoanRequestStatus.PENDING.value,
            LoanRequest.loan_id == loan_id,
        )
        .first()
    )


def list_loan_requests(
    db: Session,
    status: LoanRequestStatus | None = None,
    request_type: LoanRequestType | None = None,
    skip: int = 0,
    limit: int = 100,
) -> tuple[list[LoanRequest], int]:
    query = db.query(LoanRequest)
    if status is not None:
        query = query.filter(LoanRequest.status == status.value)
    if request_type is not None:
        query = query.filter(LoanRequest.request_type == request_type.value)

    total = query.count()
    requests = query.order_by(LoanRequest.created_at).offset(skip).limit(limit).all()
    return requests, total


def mark_approved(db: Session, loan_request: LoanRequest, reviewer_account_id: int) -> LoanRequest:
    loan_request.status = LoanRequestStatus.APPROVED.value
    loan_request.reviewer_account_id = reviewer_account_id
    loan_request.reviewed_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(loan_request)
    return loan_request


def mark_rejected(
    db: Session,
    loan_request: LoanRequest,
    reviewer_account_id: int,
    reason: str,
) -> LoanRequest:
    loan_request.status = LoanRequestStatus.REJECTED.value
    loan_request.reviewer_account_id = reviewer_account_id
    loan_request.rejection_reason = reason
    loan_request.reviewed_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(loan_request)
    return loan_request

