from datetime import datetime, timezone

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.loan import Loan, LoanStatus
from app.models.loan_operation_metric import LoanOperationMetric


def create_metric(db: Session, metric: LoanOperationMetric) -> LoanOperationMetric:
    db.add(metric)
    db.commit()
    db.refresh(metric)
    return metric


def list_metrics(db: Session) -> list[LoanOperationMetric]:
    return (
        db.query(LoanOperationMetric)
        .order_by(LoanOperationMetric.created_at, LoanOperationMetric.id)
        .all()
    )


def count_loans_by_status(db: Session, status: LoanStatus) -> int:
    return db.query(Loan).filter(Loan.status == status.value).count()


def count_overdue_loans(db: Session) -> int:
    return (
        db.query(Loan)
        .filter(
            Loan.status == LoanStatus.ACTIVE.value,
            Loan.expected_return_date < datetime.now(timezone.utc),
        )
        .count()
    )


def sum_returned_fines(db: Session) -> float:
    total = (
        db.query(func.coalesce(func.sum(LoanOperationMetric.fine_value), 0.0))
        .filter(LoanOperationMetric.operation == "loan_returned")
        .scalar()
    )
    return float(total or 0.0)


def count_events_by_operation(db: Session) -> dict[str, int]:
    rows = (
        db.query(LoanOperationMetric.operation, func.count(LoanOperationMetric.id))
        .group_by(LoanOperationMetric.operation)
        .all()
    )
    return {operation: count for operation, count in rows}
