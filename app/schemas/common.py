from pydantic import BaseModel, ConfigDict
from typing import Generic, TypeVar

T = TypeVar('T', covariant=True)

class PaginatedResponse(BaseModel, Generic[T]):
    items: list[T]
    total: int
    skip: int
    limit: int

    model_config = ConfigDict(from_attributes=True)