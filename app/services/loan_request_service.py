import logging

from sqlalchemy.orm import Session

from app.models.account import Account, AccountRole
from app.models.loan import LoanStatus
from app.models.loan_operation_metric import LoanMetricOperation
from app.models.loan_request import LoanRequest, LoanRequestStatus, LoanRequestType
from app.repositories import book_repository, loan_repository, loan_request_repository
from app.services import loan_operation_metric_service, loan_service

logger = logging.getLogger(__name__)


class ReaderAccountRequiredError(Exception):
    def __init__(self) -> None:
        self.message = "Only reader accounts can create loan requests."
        super().__init__(self.message)


class ReaderAccountMissingUserError(Exception):
    def __init__(self) -> None:
        self.message = "Reader account is not linked to a user."
        super().__init__(self.message)


class LoanRequestNotFoundError(Exception):
    def __init__(self, request_id: int) -> None:
        self.message = f"Loan request with ID {request_id} not found."
        super().__init__(self.message)


class LoanRequestAlreadyReviewedError(Exception):
    def __init__(self, request_id: int) -> None:
        self.message = f"Loan request with ID {request_id} has already been reviewed."
        super().__init__(self.message)


class DuplicatePendingLoanRequestError(Exception):
    def __init__(self) -> None:
        self.message = "A pending request already exists for this operation."
        super().__init__(self.message)


class LoanRequestBookNotFoundError(Exception):
    def __init__(self, book_id: int) -> None:
        self.message = f"Book with ID {book_id} not found for loan request."
        super().__init__(self.message)


class LoanRequestLoanNotFoundError(Exception):
    def __init__(self, loan_id: int) -> None:
        self.message = f"Loan with ID {loan_id} not found for loan request."
        super().__init__(self.message)


class LoanRequestOwnershipError(Exception):
    def __init__(self) -> None:
        self.message = "Loan does not belong to the authenticated reader."
        super().__init__(self.message)


class LoanRequestApprovalError(Exception):
    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(self.message)


def _require_reader(account: Account) -> int:
    if account.role != AccountRole.READER.value:
        raise ReaderAccountRequiredError()

    if account.user_id is None:
        raise ReaderAccountMissingUserError()

    return account.user_id


def create_loan_request(db: Session, account: Account, book_id: int) -> LoanRequest:
    operation = "create_loan_request"
    user_id = _require_reader(account)

    book = book_repository.get_book_by_id(db, book_id)
    if book is None:
        logger.warning(
            "Loan request creation blocked because book was not found",
            extra={"operation": operation, "user_id": user_id, "book_id": book_id, "reason": "book_not_found"},
        )
        raise LoanRequestBookNotFoundError(book_id)

    existing_request = loan_request_repository.get_pending_loan_request_by_user_and_book(db, user_id, book_id)
    if existing_request is not None:
        logger.warning(
            "Loan request creation blocked because pending request already exists",
            extra={
                "operation": operation,
                "user_id": user_id,
                "book_id": book_id,
                "loan_request_id": existing_request.id,
                "reason": "duplicate_pending_request",
            },
        )
        raise DuplicatePendingLoanRequestError()

    loan_request = LoanRequest(
        request_type=LoanRequestType.LOAN.value,
        status=LoanRequestStatus.PENDING.value,
        requester_account_id=account.id,
        user_id=user_id,
        book_id=book_id,
    )
    created_request = loan_request_repository.create_loan_request(db, loan_request)
    loan_operation_metric_service.record_loan_operation(
        db,
        LoanMetricOperation.LOAN_REQUEST_CREATED,
        loan_request_id=created_request.id,
        user_id=created_request.user_id,
        book_id=created_request.book_id,
        account_id=created_request.requester_account_id,
    )
    logger.info(
        "Loan request created successfully",
        extra={
            "operation": operation,
            "loan_request_id": created_request.id,
            "user_id": user_id,
            "book_id": book_id,
        },
    )
    return created_request


def create_loan_action_request(
    db: Session,
    account: Account,
    loan_id: int,
    request_type: LoanRequestType,
) -> LoanRequest:
    operation = f"create_{request_type.value}_request"
    user_id = _require_reader(account)

    loan = loan_repository.get_loan_by_id(db, loan_id)
    if loan is None:
        logger.warning(
            "Loan action request creation blocked because loan was not found",
            extra={"operation": operation, "user_id": user_id, "loan_id": loan_id, "reason": "loan_not_found"},
        )
        raise LoanRequestLoanNotFoundError(loan_id)

    if loan.user_id != user_id:
        logger.warning(
            "Loan action request creation blocked because loan belongs to another user",
            extra={"operation": operation, "user_id": user_id, "loan_id": loan_id, "reason": "loan_not_owned"},
        )
        raise LoanRequestOwnershipError()

    if loan.status != LoanStatus.ACTIVE.value:
        logger.warning(
            "Loan action request creation blocked because loan is not active",
            extra={"operation": operation, "user_id": user_id, "loan_id": loan_id, "reason": "loan_not_active"},
        )
        raise LoanRequestApprovalError("Loan must be active to request this operation.")

    existing_request = loan_request_repository.get_pending_loan_request_by_type_and_loan(db, request_type, loan_id)
    if existing_request is not None:
        logger.warning(
            "Loan action request creation blocked because pending request already exists",
            extra={
                "operation": operation,
                "user_id": user_id,
                "loan_id": loan_id,
                "loan_request_id": existing_request.id,
                "reason": "duplicate_pending_request",
            },
        )
        raise DuplicatePendingLoanRequestError()

    loan_request = LoanRequest(
        request_type=request_type.value,
        status=LoanRequestStatus.PENDING.value,
        requester_account_id=account.id,
        user_id=user_id,
        book_id=loan.book_id,
        loan_id=loan_id,
    )
    created_request = loan_request_repository.create_loan_request(db, loan_request)
    loan_operation_metric_service.record_loan_operation(
        db,
        LoanMetricOperation.LOAN_REQUEST_CREATED,
        loan_id=created_request.loan_id,
        loan_request_id=created_request.id,
        user_id=created_request.user_id,
        book_id=created_request.book_id,
        account_id=created_request.requester_account_id,
    )
    logger.info(
        "Loan request created successfully",
        extra={
            "operation": operation,
            "loan_request_id": created_request.id,
            "user_id": user_id,
            "loan_id": loan_id,
            "book_id": loan.book_id,
        },
    )
    return created_request


def list_loan_requests(
    db: Session,
    status: LoanRequestStatus | None = None,
    request_type: LoanRequestType | None = None,
    skip: int = 0,
    limit: int = 100,
) -> tuple[list[LoanRequest], int]:
    return loan_request_repository.list_loan_requests(db, status, request_type, skip, limit)


def approve_loan_request(db: Session, request_id: int, reviewer_account: Account) -> LoanRequest:
    operation = "approve_loan_request"
    loan_request = loan_request_repository.get_loan_request_by_id(db, request_id)
    if loan_request is None:
        raise LoanRequestNotFoundError(request_id)

    if loan_request.status != LoanRequestStatus.PENDING.value:
        logger.warning(
            "Loan request approval blocked because request was already reviewed",
            extra={"operation": operation, "loan_request_id": request_id, "reason": "already_reviewed"},
        )
        raise LoanRequestAlreadyReviewedError(request_id)

    try:
        if loan_request.request_type == LoanRequestType.LOAN.value:
            if loan_request.book_id is None:
                raise LoanRequestApprovalError("Loan request does not have a book_id.")
            
            loan_service.create_loan(db, loan_request.user_id, loan_request.book_id)

        elif loan_request.request_type == LoanRequestType.RETURN.value:
            if loan_request.loan_id is None:
                raise LoanRequestApprovalError("Return request does not have a loan_id.")
            
            loan_service.return_loan(db, loan_request.loan_id)

        elif loan_request.request_type == LoanRequestType.RENEWAL.value:
            if loan_request.loan_id is None:
                raise LoanRequestApprovalError("Renewal request does not have a loan_id.")
            
            loan_service.renew_loan(db, loan_request.loan_id)
            
        else:
            raise LoanRequestApprovalError("Unknown request type.")
    except loan_service.BUSINESS_RULE_EXCEPTIONS as exc:
        raise LoanRequestApprovalError(str(exc)) from exc

    approved_request = loan_request_repository.mark_approved(db, loan_request, reviewer_account.id)
    loan_operation_metric_service.record_loan_operation(
        db,
        LoanMetricOperation.LOAN_REQUEST_APPROVED,
        loan_id=approved_request.loan_id,
        loan_request_id=approved_request.id,
        user_id=approved_request.user_id,
        book_id=approved_request.book_id,
        account_id=approved_request.requester_account_id,
        reviewer_account_id=reviewer_account.id,
    )
    logger.info(
        "Loan request approved successfully",
        extra={
            "operation": operation,
            "loan_request_id": approved_request.id,
            "reviewer_account_id": reviewer_account.id,
            "request_type": approved_request.request_type,
        },
    )
    return approved_request


def reject_loan_request(
    db: Session,
    request_id: int,
    reviewer_account: Account,
    reason: str,
) -> LoanRequest:
    operation = "reject_loan_request"
    loan_request = loan_request_repository.get_loan_request_by_id(db, request_id)
    if loan_request is None:
        raise LoanRequestNotFoundError(request_id)

    if loan_request.status != LoanRequestStatus.PENDING.value:
        logger.warning(
            "Loan request rejection blocked because request was already reviewed",
            extra={"operation": operation, "loan_request_id": request_id, "reason": "already_reviewed"},
        )
        raise LoanRequestAlreadyReviewedError(request_id)

    rejected_request = loan_request_repository.mark_rejected(db, loan_request, reviewer_account.id, reason)
    loan_operation_metric_service.record_loan_operation(
        db,
        LoanMetricOperation.LOAN_REQUEST_REJECTED,
        loan_id=rejected_request.loan_id,
        loan_request_id=rejected_request.id,
        user_id=rejected_request.user_id,
        book_id=rejected_request.book_id,
        account_id=rejected_request.requester_account_id,
        reviewer_account_id=reviewer_account.id,
    )
    logger.info(
        "Loan request rejected successfully",
        extra={
            "operation": operation,
            "loan_request_id": rejected_request.id,
            "reviewer_account_id": reviewer_account.id,
            "request_type": rejected_request.request_type,
        },
    )
    return rejected_request
