from datetime import datetime, date

from pydantic import BaseModel, ConfigDict, field_serializer

from app.schemas.author import AuthorResponse


class BookCreate(BaseModel):
    isbn: str
    author_id: int
    title: str
    published_date: date

class BookResponse(BaseModel):
    id: int
    isbn: str
    title: str
    author_id: int
    author: AuthorResponse | None = None
    published_date: date
    is_available: bool
    created_at: datetime
    updated_at: datetime | None = None
    deleted_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)

    @field_serializer("created_at", "updated_at", "deleted_at")
    def serialize_datetime(self, value: datetime | None) -> str | None:
        if value is None:
            return None
        
        return value.isoformat().replace("+00:00", "Z")