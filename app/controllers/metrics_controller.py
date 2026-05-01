from fastapi import APIRouter, Depends, Response, status
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


@router.get(
    "/loans/export.csv",
    status_code=status.HTTP_200_OK,
    dependencies=[staff_only],
)
def export_loan_metrics_csv(db: Session = Depends(get_db)) -> Response:
    csv_content = loan_operation_metric_service.export_loan_operation_metrics_csv(db)
    return Response(
        content=csv_content,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": "attachment; filename=loan_operation_metrics.csv"},
    )
