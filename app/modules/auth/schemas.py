
from __future__ import annotations

from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints


KeyName = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=100),
]

OwnerId = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=128),
]


class APIKeyCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: KeyName
    # Optional quota override. None means use the server's default policy.
    monthly_quota: int | None = Field(default=None, ge=1)


class APIKeyPublic(BaseModel):
    """Safe representation of a stored API key."""

    model_config = ConfigDict(from_attributes=True, extra="forbid")

    id: int
    key_prefix: str
    name: str
    owner_id: str
    is_active: bool
    expires_at: datetime | None = None
    revoked_at: datetime | None = None
    last_used_at: datetime | None = None
    monthly_quota: int | None = None
    created_at: datetime
    updated_at: datetime


class APIKeyCreatedResponse(BaseModel):
    success: bool = True
    data: APIKeyPublic
    # This field is returned only when creating or rotating a key.
    api_key: str


class APIKeyListResponse(BaseModel):
    success: bool = True
    data: list[APIKeyPublic]
    count: int


class APIKeyResponse(BaseModel):
    success: bool = True
    data: APIKeyPublic


class APIKeyRevokeResponse(BaseModel):
    success: bool = True
    message: str = "API key revoked successfully."


class AccountSummary(BaseModel):
    """Minimal account representation for integrations with an account system.

    This project does not yet define a persistent Account model.
    """
    owner_id: OwnerId
    active_api_keys: int = Field(ge=0)
    monthly_quota: int | None = Field(default=None, ge=1)
