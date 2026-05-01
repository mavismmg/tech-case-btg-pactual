from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_serializer

from app.models.loan_request import LoanRequestStatus, LoanRequestType


class LoanRequestCreate(BaseModel):
    book_id: int = Field(..., gt=0)


class LoanActionRequestCreate(BaseModel):
    loan_id: int = Field(..., gt=0)


class LoanRequestReject(BaseModel):
    reason: str = Field(..., min_length=1, max_length=500)


class LoanRequestResponse(BaseModel):
    id: int
    request_type: LoanRequestType
    status: LoanRequestStatus
    requester_account_id: int
    reviewer_account_id: int | None = None
    user_id: int
    book_id: int | None = None
    loan_id: int | None = None
    rejection_reason: str | None = None
    created_at: datetime
    reviewed_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)

    @field_serializer("created_at", "reviewed_at")
    def serialize_datetime(self, value: datetime | None) -> str | None:
        if value is None:
            return None

        return value.isoformat().replace("+00:00", "Z")

