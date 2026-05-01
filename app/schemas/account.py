from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_serializer

from app.models.account import AccountRole


class AccountCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)
    role: AccountRole = AccountRole.LIBRARIAN
    user_id: Annotated[int, Field(gt=0)] | None = None


class AccountBootstrap(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)


class AccountLogin(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=1, max_length=128)


class AccountResponse(BaseModel):
    id: int
    name: str
    email: EmailStr
    role: AccountRole
    user_id: int | None = None
    is_active: bool
    created_at: datetime
    updated_at: datetime | None = None
    deleted_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)

    @field_serializer("created_at", "updated_at", "deleted_at")
    def serialize_datetime(self, value: datetime | None) -> str | None:
        if value is None:
            return None

        return value.isoformat().replace("+00:00", "Z")


class AccountAuthResponse(BaseModel):
    id: int
    name: str
    email: EmailStr
    role: AccountRole

    model_config = ConfigDict(from_attributes=True)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    account: AccountAuthResponse
