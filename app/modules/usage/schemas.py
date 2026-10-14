
from __future__ import annotations

from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints


RequestId = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=128),
]

EndpointName = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=255),
]

HttpMethod = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=10),
]


class UsageRecordCreate(BaseModel):
    """Internal schema for recording a completed API request."""

    model_config = ConfigDict(extra="forbid")

    api_key_id: int | None = Field(default=None, ge=1)
    request_id: RequestId | None = None
    endpoint: EndpointName
    http_method: HttpMethod
    status_code: int = Field(ge=100, le=599)
    duration_ms: float = Field(ge=0)


class UsageRecordResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    api_key_id: int | None = None
    request_id: str | None = None
    endpoint: str
    http_method: str
    status_code: int
    duration_ms: float
    occurred_at: datetime


class UsageListResponse(BaseModel):
    success: bool = True
    data: list[UsageRecordResponse]
    count: int


class UsageSummary(BaseModel):
    """Usage summary for a single UTC calendar month."""

    success: bool = True
    period_start: datetime
    period_end: datetime
    request_count: int = Field(ge=0)
    successful_requests: int = Field(ge=0)
    failed_requests: int = Field(ge=0)
    total_duration_ms: float = Field(ge=0)
    monthly_quota: int | None = Field(default=None, ge=1)
    remaining_quota: int | None = Field(default=None, ge=0)


class QuotaStatus(BaseModel):
    success: bool = True
    quota: int | None = Field(default=None, ge=1)
    used: int = Field(ge=0)
    remaining: int | None = Field(default=None, ge=0)
    exceeded: bool
    period_start: datetime
    period_end: datetime
