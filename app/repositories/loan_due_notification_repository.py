from datetime import date, datetime

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.models.loan import Loan, LoanStatus
from app.models.loan_due_notification import LoanDueNotification
from app.models.user import User


def list_due_active_loans(db: Session, start_at: datetime, end_at: datetime) -> list[Loan]:
    return (
        db.query(Loan)
        .options(joinedload(Loan.user), joinedload(Loan.book))
        .join(Loan.user)
        .filter(
            Loan.status == LoanStatus.ACTIVE.value,
            Loan.expected_return_date >= start_at,
            Loan.expected_return_date <= end_at,
            User.deleted_at.is_(None),
            User.is_active.is_(True),
        )
        .order_by(Loan.expected_return_date, Loan.id)
        .all()
    )


def get_notification(
    db: Session,
    loan_id: int,
    channel: str,
    notification_date: date,
) -> LoanDueNotification | None:
    return (
        db.query(LoanDueNotification)
        .filter(
            LoanDueNotification.loan_id == loan_id,
            LoanDueNotification.channel == channel,
            LoanDueNotification.notification_date == notification_date,
        )
        .first()
    )


def create_notification(
    db: Session,
    *,
    loan_id: int,
    channel: str,
    notification_date: date,
    status: str,
    error_message: str | None = None,
) -> LoanDueNotification:
    notification = LoanDueNotification(
        loan_id=loan_id,
        channel=channel,
        notification_date=notification_date,
        status=status,
        error_message=error_message,
    )
    db.add(notification)
    try:
        db.commit()
        db.refresh(notification)
        return notification
    except IntegrityError:
        db.rollback()
        existing = get_notification(db, loan_id, channel, notification_date)
        if existing is None:
            raise
        return existing
