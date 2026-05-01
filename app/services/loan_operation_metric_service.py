import logging

from sqlalchemy.orm import Session

from app.models.loan import LoanStatus
from app.models.loan_operation_metric import LoanMetricOperation, LoanOperationMetric
from app.repositories import loan_operation_metric_repository
from app.schemas.loan_operation_metric import LoanMetricsSummaryResponse

logger = logging.getLogger(__name__)


def record_loan_operation(
    db: Session,
    operation: LoanMetricOperation,
    loan_id: int | None = None,
    loan_request_id: int | None = None,
    user_id: int | None = None,
    book_id: int | None = None,
    account_id: int | None = None,
    reviewer_account_id: int | None = None,
    fine_value: float | None = None,
) -> LoanOperationMetric | None:
    metric = LoanOperationMetric(
        operation=operation.value,
        loan_id=loan_id,
        loan_request_id=loan_request_id,
        user_id=user_id,
        book_id=book_id,
        account_id=account_id,
        reviewer_account_id=reviewer_account_id,
        fine_value=fine_value,
    )

    try:
        return loan_operation_metric_repository.create_metric(db, metric)
    except Exception:
        db.rollback()
        logger.warning(
            "Loan operation metric recording failed",
            extra={
                "operation": "record_loan_operation_metric",
                "metric_operation": operation.value,
                "loan_id": loan_id,
                "loan_request_id": loan_request_id,
                "user_id": user_id,
                "book_id": book_id,
            },
            exc_info=True,
        )
        return None


def get_loan_metrics_summary(db: Session) -> LoanMetricsSummaryResponse:
    active_loans = loan_operation_metric_repository.count_loans_by_status(db, LoanStatus.ACTIVE)
    returned_loans = loan_operation_metric_repository.count_loans_by_status(db, LoanStatus.RETURNED)

    return LoanMetricsSummaryResponse(
        total_loans=active_loans + returned_loans,
        active_loans=active_loans,
        overdue_loans=loan_operation_metric_repository.count_overdue_loans(db),
        returned_loans=returned_loans,
        total_fine_value=loan_operation_metric_repository.sum_returned_fines(db),
        events_by_operation=loan_operation_metric_repository.count_events_by_operation(db),
    )
