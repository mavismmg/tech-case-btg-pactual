from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.dependencies import get_db, require_roles
from app.models.account import AccountRole
from app.schemas.notification import DueLoanNotificationResponse, NotificationChannel
from app.services import notification_service

router = APIRouter(prefix="/notifications", tags=["Notifications"])
staff_only = Depends(require_roles(AccountRole.ADMIN, AccountRole.LIBRARIAN))


@router.post(
    "/due-loans/send",
    response_model=DueLoanNotificationResponse,
    status_code=status.HTTP_200_OK,
    dependencies=[staff_only],
)
def send_due_loan_notifications(
    days_ahead: Annotated[int, Query(ge=0, le=30)] = 1,
    channel: NotificationChannel = NotificationChannel.ALL,
    db: Session = Depends(get_db),
) -> DueLoanNotificationResponse:
    return notification_service.send_due_loan_notifications(db, days_ahead=days_ahead, channel=channel)
