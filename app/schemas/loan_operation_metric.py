from pydantic import BaseModel, ConfigDict


class LoanMetricsSummaryResponse(BaseModel):
    total_loans: int
    active_loans: int
    overdue_loans: int
    returned_loans: int
    total_fine_value: float
    events_by_operation: dict[str, int]

    model_config = ConfigDict(from_attributes=True)
