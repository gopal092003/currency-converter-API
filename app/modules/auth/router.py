from __future__ import annotations

from typing import Annotated

from app.db.models.api_key import APIKey
from app.db.session import get_db
from app.modules.auth.schemas import (
    APIKeyCreatedResponse,
    APIKeyCreateRequest,
    APIKeyListResponse,
    APIKeyPublic,
    APIKeyRevokeResponse,
)
from app.modules.auth.service import APIKeyService
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

router = APIRouter(prefix="/auth/api-keys", tags=["API keys"])

DBSession = Annotated[Session, Depends(get_db)]


def get_authenticated_api_key(request: Request) -> APIKey:
    """Read the validated caller identity from server-side request state."""
    record = getattr(request.state, "api_key", None)

    if not isinstance(record, APIKey):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Valid API-key authentication is required",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    if not record.is_active or record.revoked_at is not None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Valid API-key authentication is required",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    return record


CurrentAPIKey = Annotated[
    APIKey,
    Depends(get_authenticated_api_key),
]


@router.post(
    "",
    response_model=APIKeyCreatedResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_api_key(
    payload: APIKeyCreateRequest,
    db: DBSession,
    current_key: CurrentAPIKey,
) -> APIKeyCreatedResponse:
    service = APIKeyService(db)
    record, raw_key = service.create_key(
        owner_id=current_key.owner_id,
        name=payload.name,
        monthly_quota=payload.monthly_quota,
    )
    return APIKeyCreatedResponse(
        data=APIKeyPublic.model_validate(record),
        api_key=raw_key,
    )


@router.get("", response_model=APIKeyListResponse)
def list_api_keys(
    db: DBSession,
    current_key: CurrentAPIKey,
) -> APIKeyListResponse:
    records = APIKeyService(db).list_keys(owner_id=current_key.owner_id)
    return APIKeyListResponse(
        data=[APIKeyPublic.model_validate(record) for record in records],
        count=len(records),
    )


@router.post(
    "/{key_id}/rotate",
    response_model=APIKeyCreatedResponse,
)
def rotate_api_key(
    key_id: int,
    db: DBSession,
    current_key: CurrentAPIKey,
) -> APIKeyCreatedResponse:
    service = APIKeyService(db)
    record, raw_key = service.rotate_key(
        key_id=key_id,
        owner_id=current_key.owner_id,
    )
    return APIKeyCreatedResponse(
        data=APIKeyPublic.model_validate(record),
        api_key=raw_key,
    )


@router.delete(
    "/{key_id}",
    response_model=APIKeyRevokeResponse,
)
def revoke_api_key(
    key_id: int,
    db: DBSession,
    current_key: CurrentAPIKey,
) -> APIKeyRevokeResponse:
    APIKeyService(db).revoke_key(
        key_id=key_id,
        owner_id=current_key.owner_id,
    )
    return APIKeyRevokeResponse()
