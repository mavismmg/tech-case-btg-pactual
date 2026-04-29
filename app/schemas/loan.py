from pydantic import BaseModel, ConfigDict, field_serializer
from datetime import datetime

class LoanCreate(BaseModel):
    user_id: int
    book_id: int

class LoanResponse(BaseModel):
    id: int
    user_id: int
    book_id: int
    loan_date: datetime
    expected_return_date: datetime
    actual_return_date: datetime | None
    fine_value: float
    status: str

    model_config = ConfigDict(from_attributes=True)

    @field_serializer("loan_date", "expected_return_date", "actual_return_date")
    def serialize_datetime(self, value: datetime | None) -> str | None:
        if value is None:
            return None
        
        return value.isoformat().replace("+00:00", "Z")