from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.dependencies import get_db, require_roles
from app.models.account import AccountRole
from app.schemas.loan_operation_metric import LoanMetricsSummaryResponse
from app.services import loan_operation_metric_service

router = APIRouter(prefix="/metrics", tags=["Metrics"])
staff_only = Depends(require_roles(AccountRole.ADMIN, AccountRole.LIBRARIAN))


@router.get(
    "/loans",
    response_model=LoanMetricsSummaryResponse,
    status_code=status.HTTP_200_OK,
    dependencies=[staff_only],
)
def get_loan_metrics(db: Session = Depends(get_db)) -> LoanMetricsSummaryResponse:
    return loan_operation_metric_service.get_loan_metrics_summary(db)
