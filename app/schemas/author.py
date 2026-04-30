from pydantic import BaseModel, ConfigDict, field_serializer
from datetime import datetime

class AuthorCreate(BaseModel):
    name: str

class AuthorResponse(BaseModel):
    id: int
    name: str
    created_at: datetime
    updated_at: datetime | None
    deleted_at: datetime | None

    model_config = ConfigDict(from_attributes=True)

    @field_serializer("created_at", "updated_at", "deleted_at")
    def serialize_datetime(self, value: datetime | None) -> str | None:
        if value is None:
            return None
        
        return value.isoformat().replace("+00:00", "Z")